"""drivers/p22_probe.py (Plan 22, the agent-base probe: X1 motor arms, X2 emit bench, X3 heavy-load drain), offline: the
driver is never invoked.

The phases run against FakeModP, test_a_pipe_3's FakeMod3 (the scan in parts) with the probe's Lua shapes
(probe-interface.md §§ 1-5): a 0.2 hello and its `bench` line; `goto x y [arm]` walking at WALK_TPS or RUN_TPS by arm;
`autowalk dx dy s [arm]` along the commanded vector (an optional heading error); `drop <fullType> <n>`; an RCON
`additem` (the test's stand-in for xs.rcon) raising the load unless it stalls; frames carrying
moving, running, sprinting, endurance, weight, maxWeight, moodles.HEAVY_LOAD and motor {forceRun, autoWalk,
updRunning, updForceRun}; a health that falls 0.39 every DROP_EVERY frames while HEAVY_LOAD >= the drop level and the
character moves (and health > 75 unless the floor is off); a `damage` event per drop when the client hears. The fake
bus answers bench.global, fall.probe, event.watch, stats.all and ping with their handlers' reply shapes
(docs/reference/harness-commands.md).

The fake maps an autowalk's input vector to the world as the engine does (IsoPlayer.updateMovementFromInput
L3025-L3026: world x = iy + ix, world y = iy - ix; mapping="identity" leaves it as sent), so the autowalk tests pass
only when the driver's rotation into input space is right. The probe's own autowalk legs (3 s walks, 1.5 s runs, each re-centred) stay on the 12-square strip at the fake's 1.6
and 3.2 tiles/s; a 4.5 tiles/s run voids the running legs. The 20 degree heading case runs 1 s legs (SHORT_AUTOWALK),
since a 4.8-tile leg at 20 degrees crosses the side row and voids."""
import math
import os

import pytest

from agent.drivers import p22_probe as D
from agent.link import Link
from . import test_a_pipe as T1
from . import test_a_pipe_3 as T3

REPO = T1.REPO
X = D.X
REAL_AUTOWALK = list(D.AUTOWALK_LEGS)
SHORT_AUTOWALK = [(dx, dy, 1.0, arm) for dx, dy, _, arm in REAL_AUTOWALK]

BENCH_INFO = {"json21Bytes": 2560, "compactBytes": 1600, "noSortBytes": 2560, "squares": 20}
BENCH_US = {"json": 900.0, "jsonNoSort": 700.0, "compact": 400.0, "concat": 5.0, "openWrite": 600.0,
            "openWrite20": 300.0, "openOnly": 280.0, "poll": 150.0, "heldOpen": 250.0, "heldWrite": 40.0,
            "heldClose": 30.0}


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
    assert os.path.basename(D.__file__) == D.DRIVER == D.KEY + ".py" == "p22_probe.py"
    assert D.KEY == "p22_probe" and D.ARTIFACT == "p22_probe.json" and D.USER == "admin"
    assert D.PROFILE == "testing/profiles/agent-nozombies.toml" and os.path.isfile(os.path.join(REPO, D.PROFILE))
    assert D.BUDGET_S == 720.0 and D.MIN_FREE_GB == D.DL.MIN_FREE_GB and D.X1_DEADLINE_S == 450.0


def test_every_constant_of_the_brief_is_in_constants():
    c = D.CONSTANTS
    want = {"BUDGET_S": 720.0, "X1_DEADLINE_S": 450.0, "CALIBRATE_TOL_DEG": 15.0, "CALIBRATE_LEG": (1, 0, 1.5, "walk"), "LINE_LEN": 12, "BENCH_REPS": 3, "LEGS_PER_ARM": 3, "SETTLE_S": 3.0,
            "GOAL_TIMEOUT_S": 40.0, "TOGGLE_IF_BELOW": 1.3, "LOAD_MAX_ADDS": 14, "LOAD_ITEM": "Base.Plank",
            "LOAD_SETTLE_S": 5.0, "WALK_S": 30.0, "STILL_S": 15.0, "PLANK_W": 3.0, "WALK2_S": 15.0,
            "HEALTH_FLOOR": 75.0, "HEAVY_LEVEL": 3, "LEVEL2_RATIO": 1.25, "LEVEL3_RATIO": 1.5, "LEVEL4_RATIO": 1.75,
            "RUN_RATIO": 1.3, "SETRUN_TOL": 0.05, "HEADING_MAX_DEG": 15.0, "ONCE_HOLD_FRAC": 0.9, "DROP_EPS": 0.05,
            "MOD_VERSION": "0.2"}
    for k, v in want.items():
        assert c[k] == v, k
    assert c["BENCH_ARMS"] == [("json", 500), ("jsonNoSort", 500), ("compact", 500), ("concat", 500),
                               ("openWrite", 500), ("openWrite20", 500), ("openOnly", 500), ("poll", 500)]
    assert c["HELD_ARMS"] == [("heldOpen", 1), ("heldWrite", 500), ("heldClose", 1)]
    assert c["MOTOR_ARMS"] == ["walk", "setrun", "forcerun", "forcerun_tick", "forcesprint"]
    assert c["AUTOWALK_LEGS"] == [(1, 0, 3.0, "walk"), (-1, 0, 1.5, "forcerun"), (2, 0, 1.5, "forcerun"),
                                  (-1.95, 0, 1.5, "once"), (1, 0, 1.5, "forcerun"), (-1, 0, 3.0, "walk")]
    assert c["X1_RATE_HZ"] == 10 and c["X1_RATE_BACK_HZ"] == 5 and "10 Hz" in D.__doc__
    assert set(D.US_PER_KB_ARMS) == {"json", "jsonNoSort", "compact", "openWrite", "heldWrite"}
    assert c["MOVE_EPS_TILES"] == D.AP4.MOVE_EPS_TILES
    for name in ("pace", "endurance slope", "flags", "heading error", "PREDICTIONS", "not gates", "RULES",
                 "PZA.now()", "time.time()", "launched detached", "never -safemode"):
        assert name in D.__doc__, name
    for g in ("x1_forcerun_runs", "x1_setrun_walks", "x1_autowalk_runs", "x1_autowalk_heads", "x1_forcerun_tick",
              "x1_once_holds", "x1_endurance", "x3_drops_at_level3_only", "x3_floor_75", "x3_drops_while_still",
              "x3_level2_no_drop", "x3_server_hears_heavyload", "x3_client_hears_heavyload", "x3_level3_at_ratio"):
        assert g in D.__doc__ and g in D.PREDICTIONS, g


def test_the_frozen_drivers_are_imported_never_copied_over():
    src = open(D.__file__, encoding="utf-8").read()
    for name in ("a_pipe as AP", "a_pipe_2 as AP2", "a_pipe_4 as AP4"):
        assert "from agent.drivers import %s" % name in src
    assert issubclass(D.Probe, D.AP2.Pipe2) and D.AP2.KEY == "a_pipe_2" and D.AP4.KEY == "a_pipe_4"
    assert "AP4.first_move(" in src and "def first_move" not in src
    assert "make_client=AP.clearing_make_client(session.make_client)" in src
    assert "AP.memory_gate(xs)" in src


# ================================================================ pre-boot
def test_preboot_on_the_real_profile(agent_fixture, monkeypatch):
    monkeypatch.setattr(D.DL.C, "doctor", lambda: (True, "ok"))
    monkeypatch.setattr(D.DL.harness, "lint_paths", lambda srcs: [])
    dirty = {"v": None}
    monkeypatch.setattr(D.DL.C, "git_dirty", lambda rel: (rel == dirty["v"], ""))
    real = D.DL.C.git_say
    tracked = {"v": ""}
    monkeypatch.setattr(D.DL.C, "git_say", lambda *a: tracked["v"] if a[0] == "ls-files" else real(*a))
    pre, ok = D.preboot(D.__file__)
    assert ok, pre
    assert pre["profile"] == "agent-nozombies" and pre["driver_checks"] == {
        "driver_file": True, "driver_prefix": True, "profile_exists": True, "no_committed_artifact": True,
        "agent_lua_dirty": False, "driver_dirty": False, "agent_py_dirty": False}
    dirty["v"] = "testing/PZAgent"
    pre, ok = D.preboot(D.__file__)
    assert not ok and pre["driver_checks"]["agent_lua_dirty"] is True
    dirty["v"] = "testing/agent"
    pre, ok = D.preboot(D.__file__)
    assert not ok and pre["driver_checks"]["agent_py_dirty"] is True
    dirty["v"] = None
    tracked["v"] = "testing/artifacts/p22_probe-20261027-120000/p22_probe.json"
    pre, ok = D.preboot(D.__file__)
    assert not ok and pre["driver_checks"]["no_committed_artifact"] is False
    tracked["v"] = ""
    assert D.preboot(os.path.join(os.path.dirname(D.__file__), "a_pipe_4.py"))[1] is False


# ================================================================ choose_line
def grid(x0, x1, y0, y1, z=0):
    return {(x, y, z): {"x": x, "y": y, "z": z, "solid": False, "solidTrans": False}
            for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}


def test_choose_line_picks_the_nearest_open_run_with_its_side_rows():
    sq = grid(0, 20, 0, 6)
    got = D.choose_line(sq, (2.5, 3.5))
    assert (got["ax"], got["ay"], got["bx"], got["by"], got["dir"]) == (2, 3, 13, 3, "+x") and got["dist"] == 0
    assert got["candidates"] > 0
    sq[(5, 3, 0)]["solidTrans"] = True                      # one square of that run and of its neighbours' side rows
    got = D.choose_line(sq, (2.5, 3.5))
    assert (got["ax"], got["ay"], got["bx"], got["by"], got["dir"]) == (2, 1, 13, 1, "+x") and got["dist"] == 2


def test_a_run_ending_nearer_the_player_is_taken_from_that_end():
    sq = grid(0, 11, 0, 2)
    got = D.choose_line(sq, (11.5, 1.5))
    assert (got["ax"], got["ay"], got["bx"], got["by"], got["dir"]) == (11, 1, 0, 1, "-x")


@pytest.mark.parametrize("bad", [{"solidTrans": True}, {"solid": True}, {"room": "kitchen"}, {"building": 7},
                                 {"door": {"open": False}}, {"window": {"open": False}}, None])
def test_one_blocked_roomed_or_doored_square_rejects_the_only_run(bad):
    sq = grid(0, 11, 0, 2)
    assert D.choose_line(sq, (0.5, 1.5)) is not None
    if bad is None:
        del sq[(6, 2, 0)]                                    # a side-row square the scan lacks
    else:
        sq[(6, 1, 0)].update(bad)
    assert D.choose_line(sq, (0.5, 1.5)) is None


def test_choose_line_falls_back_to_none_and_keeps_to_the_players_z():
    assert D.choose_line({}, (0.5, 0.5)) is None
    assert D.choose_line(grid(0, 11, 0, 2, z=1), (0.5, 1.5), z=0) is None
    assert D.choose_line(grid(0, 11, 0, 2, z=1), (0.5, 1.5), z=1)["ay"] == 1


# ================================================================ the readings on hand-built frames
def F(seq, x, y, wall, moving=True, **kw):
    f = {"seq": seq, "x": x, "y": y, "wallMs": wall, "moving": moving}
    f.update(kw)
    return f


def test_pace_sums_moving_pairs_over_the_moving_span():
    fr = [F(1, 0, 0, 0, moving=False), F(2, 0, 0, 1000), F(3, 3, 4, 2000), F(4, 6, 8, 3000),
          F(5, 9, 8, 9000, moving=False)]
    assert D.pace(fr) == pytest.approx(10 / 2.0)
    assert D.pace([F(1, 0, 0, 0), F(2, 1, 0, 0)]) is None            # a zero span
    assert D.pace([F(1, 0, 0, 0), F(2, 5, 0, 1000, moving=False)]) is None      # under 2 moving frames
    assert D.pace([]) is None


def test_endurance_slope_and_flags():
    fr = [F(1, 0, 0, 1000, endurance=0.9, running=True, motor={"forceRun": True, "updForceRun": True}),
          F(2, 1, 0, 3000, endurance=0.8, sprinting=True, motor={"autoWalk": True, "updRunning": True}),
          F(3, 2, 0, 5000, endurance=0.7, motor="missing")]
    assert D.endurance_slope(fr) == pytest.approx(-0.2 / 4.0)
    assert D.endurance_slope(fr[:1]) is None
    assert D.flags(fr) == {"running": 1, "sprinting": 1, "forceRun": 1, "updRunning": 1, "updForceRun": 1,
                           "autoWalk": 1, "frames": 3}


def test_heading_error_and_displacement():
    fr = [F(1, 0, 0, 0), F(2, 1, 0.1, 100), F(3, 2, 2 * math.tan(math.radians(20)), 200)]
    assert D.heading_error_deg(fr, 1, 0) == pytest.approx(20)
    assert D.heading_error_deg(fr, -1.95, 0) == pytest.approx(160)
    assert D.displacement(fr) == pytest.approx(math.hypot(2, 2 * math.tan(math.radians(20))))
    assert D.heading_error_deg(fr[:1], 1, 0) is None and D.displacement(fr[:1]) is None
    assert D.heading_error_deg([F(1, 0, 0, 0), F(2, 0, 0, 1)], 1, 0) is None


def test_unload_count_aims_at_level_two():
    assert D.unload_count(13.0, 8.0, 4) == (1, pytest.approx(10 / 8), "level2 band")
    k, r, why = D.unload_count(12.5, 8.0, 4)                 # 9.5 is below 10 and 12.5 is not below 12
    assert (k, why) == (1, "below level 3") and r == pytest.approx(9.5 / 8)
    assert D.unload_count(30.0, 8.0, 2)[0::2] == (2, "every plank")
    assert D.unload_count(None, 8.0, 3)[0] == 3


def test_drops_carry_the_frame_befores_level_and_the_window():
    tr = [{"seq": 1, "health": 100, "level": 3, "moving": True}, {"seq": 2, "health": 99.6, "level": 3, "moving": True},
          {"seq": 3, "health": 99.58, "level": 2, "moving": False}, {"seq": 4, "health": 99.0, "level": 2,
                                                                       "moving": False}]
    d = D.drops_of(tr, {"walk_loaded": (0, 2), "still": (2, 4)})
    assert [(x["seq"], x["level"], x["moving"], x["window"]) for x in d] == [(2, 3, True, "walk_loaded"),
                                                                            (4, 2, False, "still")]


# ================================================================ the probe against FakeModP
class FakeModP(T3.FakeMod3):
    WALK_TPS = 1.6
    RUN_TPS = 3.2
    MAXW = 8.0
    LOAD0 = 1.0
    DROP = 0.39
    DONE_R = 1.0

    def __init__(self, d, clock, version="0.2", forcerun_runs=True, heading_err=0.0, drop_level=3, floor=True,
                 drop_every=1, client_hears=False, server_heavy=True, once_holds=True, setrun_runs=False,
                 endurance_flat=False, level3_from=1.5, blocked=(), run_tps=None, mapping="engine", **kw):
        super().__init__(d, clock, **kw)
        self.version, self.forcerun_runs, self.heading_err = version, forcerun_runs, heading_err
        self.drop_level, self.floor, self.drop_every = drop_level, floor, drop_every
        self.client_hears, self.server_heavy, self.once_holds = client_hears, server_heavy, once_holds
        self.setrun_runs, self.endurance_flat, self.level3_from = setrun_runs, endurance_flat, level3_from
        self.blocked = set(blocked)
        self.mapping = mapping
        if run_tps is not None:
            self.RUN_TPS = run_tps
        self.pg = None
        self.load = self.LOAD0
        self.endurance = 1.0
        self.moving, self.fast, self.arm, self.kind = False, False, None, None
        self.drops = self.client_count = self.frames_n = 0
        self.goals = []

    def level(self):
        r = self.load / self.MAXW
        return 4 if r >= 1.75 else 3 if r >= self.level3_from else 2 if r >= 1.25 else 1 if r >= 1.0 else 0

    def speed(self, arm):
        if arm == "toggle" or (arm == "setrun" and self.setrun_runs):
            return self.RUN_TPS
        if arm in ("forcerun", "forcesprint"):
            return self.RUN_TPS if self.forcerun_runs else self.WALK_TPS
        if arm == "once":
            return self.RUN_TPS if self.forcerun_runs and self.once_holds else self.WALK_TPS
        return self.WALK_TPS

    def poll(self):
        cmd = super().poll()
        if self.job is not None and not self.job.get("fixed"):
            for s in self.job["squares"]:
                s["solidTrans"] = (s["x"], s["y"]) in self.blocked
            self.job["fixed"] = True
        if cmd and cmd["goal"] in ("goto", "autowalk", "drop"):
            self.cmds.append(cmd)
            ok, reason = self.start(cmd)
            self.emit("ack", {"cmdSeq": cmd["seq"], "ok": ok, "reason": reason})
            self.flush()
            cmd = None
        self.advance()
        return cmd

    def start(self, cmd):
        a = cmd["args"].split()
        g = {"seq": cmd["seq"], "name": cmd["goal"], "state": "running", "detail": "", "ticks": 0,
             "x0": self.x, "y0": self.y}
        if cmd["goal"] == "goto":
            g.update(tx=float(a[0]), ty=float(a[1]), arm=a[2] if len(a) > 2 else "walk")
        elif cmd["goal"] == "autowalk":
            ix, iy = float(a[0]), float(a[1])
            wx, wy = (ix, iy) if self.mapping == "identity" else (iy + ix, iy - ix)     # the engine's L3025-L3026
            g.update(dx=wx, dy=wy, ix=ix, iy=iy, s=float(a[2]), arm=a[3] if len(a) > 3 else "walk")
        else:
            g.update(k=int(a[1]), arm=None)
        self.pg = g
        self.goals.append(dict(g))
        return True, ""

    def status(self):
        g = self.pg
        if g is None:
            return {"seq": 0, "name": "idle", "state": "idle", "detail": ""}
        if g["state"] != "running":
            g["reported"] = True
        return {"seq": g["seq"], "name": g["name"], "state": g["state"], "detail": g["detail"]}

    def advance(self):
        self.moving, self.fast, self.arm, self.kind = False, False, None, None
        g = self.pg
        if g is not None and g["state"] != "running":
            if g.get("reported"):
                self.pg = None
            g = None
        if g is not None:
            g["ticks"] += 1
            if g["name"] == "drop":
                if g["ticks"] >= 30:
                    self.load -= g["k"] * D.PLANK_W
                    g["state"], g["detail"] = "done", "moved=%d" % g["k"]
            else:
                v = self.speed(g["arm"]) / self.TPS
                self.arm, self.kind = g["arm"], g["name"]
                if g["name"] == "goto":
                    ex, ey = g["tx"] - self.x, g["ty"] - self.y
                    d = math.hypot(ex, ey)
                    if d <= self.DONE_R:
                        g["state"], g["detail"] = "done", "d=%s" % d
                    else:
                        st = min(v, d)
                        self.x += ex / d * st
                        self.y += ey / d * st
                        self.moving, self.fast = True, v * self.TPS > self.WALK_TPS
                else:
                    if g["ticks"] > g["s"] * self.TPS:
                        g["state"] = "done"
                        g["detail"] = "d=%s" % math.hypot(self.x - g["x0"], self.y - g["y0"])
                    else:
                        n = math.hypot(g["dx"], g["dy"])
                        th = math.atan2(g["dy"], g["dx"]) + math.radians(self.heading_err)
                        self.x += math.cos(th) * v
                        self.y += math.sin(th) * v
                        self.moving, self.fast = n > 0, v * self.TPS > self.WALK_TPS
        if self.endurance_flat:
            pass
        elif self.moving:
            self.endurance = max(0.0, self.endurance - (0.0002 if self.fast else 0.00002))
        else:
            self.endurance = min(1.0, self.endurance + 0.0001)

    def motor(self):
        arm, kind = self.arm, self.kind
        forced = arm in ("forcerun", "forcesprint", "toggle", "forcerun_tick") or (
            kind == "autowalk" and arm == "forcerun") or (kind == "autowalk" and arm == "once" and self.once_holds)
        upd = arm in ("forcerun", "forcesprint", "toggle") or (kind == "autowalk" and forced)
        return {"forceRun": forced, "forceSprint": arm == "forcesprint", "autoWalk": kind == "autowalk",
                "updRunning": self.fast, "updForceRun": upd, "updSprinting": False, "upd": self.tick, "updErrors": 0}

    def emit(self, kind, body):
        dmg = False
        if kind == "hello":
            body["modVersion"] = self.version
        if kind == "frame":
            self.frames_n += 1
            lv = self.level()
            if (self.moving and lv >= self.drop_level and (not self.floor or self.health > D.HEALTH_FLOOR)
                    and self.frames_n % self.drop_every == 0):
                self.health -= self.DROP
                self.drops += 1
                dmg = True
            body.update(moving=self.moving, running=self.arm == "setrun" or self.fast, sprinting=self.arm == "setrun",
                        endurance=self.endurance, weight=self.load, maxWeight=self.MAXW,
                        moodles={"HUNGRY": 0, "HEAVY_LOAD": lv}, motor=self.motor())
        super().emit(kind, body)
        if kind == "hello" and self.version == D.MOD_VERSION:
            T1.FakeMod.emit(self, "bench", dict(BENCH_INFO))
        if dmg and self.client_hears:
            self.client_count += 1
            T1.FakeMod.emit(self, "event", {"event": "damage", "tag": "HEAVYLOAD", "amount": self.DROP,
                                            "isLocal": True})


def make_probe(tmp_path, budget_s=1e9, bench_error=(), stall=False, **flags):
    clock = T1.Clock()
    sd = str(tmp_path / "clients" / "admin" / "Lua" / "pzagent" / "admin")
    mod = FakeModP(sd, clock, **flags)
    out = D.new_out()
    calls = []

    def ask(node, cmd, args, timeout=30):
        calls.append((node, cmd, args))
        mod.sleep(0.05)
        a = args.split()
        if cmd == "ping":
            return "pong"
        if cmd == "bench.global":
            name, n = a[0].split(".")[-1], int(a[1])
            if name in bench_error:
                return {"side": "client", "name": a[0], "error": "attempted index: w of non-table"}
            if name == "nonDict":
                return "no such global"
            us = BENCH_US[name]
            return {"side": "client", "name": a[0], "n": n, "ms": us * n / 1000.0, "usPerCall": us}
        if cmd == "fall.probe":
            counts = {"HEAVYLOAD": mod.drops} if mod.server_heavy else {}
            return {"ok": True, "side": "server", "hooked": True, "fall": {}, "counts": counts, "legs": {},
                    "maxFracture": 0}
        if cmd == "event.watch":
            return {"ok": True, "side": "client", "event": a[0], "hooked": True, "count": mod.client_count,
                    "fires": [{"wallMs": 1}] * mod.client_count}
        return {"ok": True, "user": args, "stats": {"HUNGER": 0.1}}

    xs = X.Xs(out, node=lambda side: side, ask=ask, clock=clock.now, sleep=mod.sleep, budget_s=budget_s,
              user="admin", predictions=D.PREDICTIONS)
    xs.path = str(tmp_path / D.ARTIFACT)

    def rcon(cmd, tag):                       # xs.rcon's stand-in: the reply shape {ok, reply}
        calls.append(("rcon", cmd, tag))
        mod.sleep(0.05)
        if not stall:
            mod.load += D.PLANK_W
        return {"ok": True, "reply": "Item Base.Plank added to admin's inventory"}
    xs.rcon = rcon
    probe = D.Probe(xs, Link(sd, clock=clock.now), clock=clock.now, sleep=mod.sleep)
    return probe, out, mod, calls


def run_phases(probe, names):
    for name, fn in probe.phases():
        if name in names:
            probe.xs.run_phase(name, fn)
            probe.sync_out()


def verdicts(out, prefix):
    return {k: v["verdict"] for k, v in out["verdicts"].items() if k.startswith(prefix)}


@pytest.fixture(scope="module")
def clean_run(tmp_path_factory):
    probe, out, mod, calls = make_probe(tmp_path_factory.mktemp("clean"))
    probe.run()
    return probe, out, mod, calls


def test_a_correct_mod_records_every_reading_and_every_grade_as_predicted(clean_run):
    probe, out, mod, calls = clean_run
    assert out["phase_errors"] == {} and "budget_stop" not in out and "abort" not in out, out["phase_errors"]
    assert out["hello"]["modVersion"] == "0.2" and out["bench_info"]["json21Bytes"] == 2560
    rd = out["readings"]
    assert sorted(rd) == ["bench", "line", "load", "motor", "server"]
    line = rd["line"]
    assert (line["ax"], line["ay"], line["bx"], line["by"], line["dir"]) == (100, 200, 111, 200, "+x")
    assert line["scan"]["done"] and line["candidates"] > 0 and "fallback" not in line
    # X2
    rows = rd["bench"]["rows"]
    assert len(rows) == D.BENCH_REPS * (len(D.BENCH_ARMS) + len(D.HELD_ARMS)) and not any(r["error"] for r in rows)
    s = rd["bench"]["summary"]
    assert s["json"]["median_usPerCall"] == 900.0 and s["json"]["us_per_kb"] == pytest.approx(900.0 / 2.5)
    assert s["compact"]["us_per_kb"] == pytest.approx(400.0 / (1600 / 1024))
    assert s["heldWrite"]["bytes"] == 2560 and s["openWrite20"]["bytes"] == 20 and "us_per_kb" not in s["poll"]
    assert ("client", "bench.global", "PZA.bench.heldWrite 500") in calls
    # X1
    m = rd["motor"]
    assert m["approach"]["arm"] == "approach" and m["return"]["arm"] == "return"
    assert [r["arm"] for r in m["legs"]] == [a for a in D.MOTOR_ARMS for _ in range(3)]
    ends = [r["to"]["end"] for r in m["legs"]]
    assert ends == ["B", "A"] * 7 + ["B"] and all(r["error"] is None for r in m["legs"])
    for r in m["legs"]:
        assert r["goal"]["state"] == "done" and r["frames"] > 5 and r["first_move"] is not None
        assert r["cmd_move_ms"] is not None and r["cmd_move_ms"] >= 0 and r["flags"]["frames"] == r["frames"]
    assert m["paces"]["walk"] == pytest.approx(1.6) and m["paces"]["forcerun"] == pytest.approx(3.2)
    assert m["paces"]["setrun"] == pytest.approx(1.6) and m["toggle"] == []
    assert m["toggle_skipped"]["forcerun"] == pytest.approx(3.2)
    gotos = [c["args"] for c in mod.cmds if c["goal"] == "goto"]
    assert gotos[0] == "100.5 200.5" and gotos[1] == "111.5 200.5" and gotos[4] == "100.5 200.5 setrun"
    aw = m["autowalk"]
    assert [c["args"] for c in mod.cmds if c["goal"] == "autowalk"] == [
        "0.707107 0.707107 1.5", "0.707107 0.707107 3.0", "-0.707107 -0.707107 1.5 forcerun",
        "1.414214 1.414214 1.5 forcerun", "-1.378858 -1.378858 1.5 once", "0.707107 0.707107 1.5 forcerun",
        "-0.707107 -0.707107 3.0"]
    cal = m["autowalk_calibration"]
    assert cal["arm"] == "walk" and cal["leg"] == "calibration" and (cal["vx"], cal["vy"]) == (1.0, 0.0)
    assert cal["heading_signed_deg"] == pytest.approx(0, abs=1e-6) and m["autowalk_correction_deg"] == 0
    assert all(r["correction_deg"] == 0 and (r["ix"], r["iy"]) == D.input_vector(r["vx"], r["vy"]) for r in aw)
    assert all(r["heading_error_deg"] == pytest.approx(0, abs=1e-6) and r["displacement"] > 1.0 for r in aw)
    assert not any(r["voided"] for r in aw) and line["strip_squares"] == 36
    assert len(m["centre"]) == 7 and all(r["arm"] == "centre" and r["to"]["x"] == 106.0 for r in m["centre"])
    assert m["deadline_skipped"] == 0 and all(r["frames"] >= 10 for r in aw)      # 10 Hz: a 1.5 s leg's frames
    # the config commands: rate 10 after the approach, every leg between, rate 5 at X1's end (before X3's adds)
    seq = [(c["goal"], c["args"]) for c in mod.cmds if c["goal"] in ("rate", "goto", "autowalk")]
    i10, i5 = seq.index(("rate", "10")), seq.index(("rate", "5"))
    assert seq[0] == ("goto", "100.5 200.5") and i10 == 1 and [g for g, _ in seq].count("rate") == 2
    x1 = seq[i10 + 1:i5]
    assert len([g for g, _ in x1 if g == "goto"]) == 15 + 7 + 1 and len([g for g, _ in x1 if g == "autowalk"]) == 7
    assert all(g == "goto" for g, a in seq[i5 + 1:])                  # X3's legs only after rate 5
    assert m["rate_on"]["ack"]["ok"] and m["rate_back"]["ack"]["ok"] and mod.rate == 5
    assert gotos[16] == "106.0 200.5" and line["targets"]["M"] == [106.0, 200.5]
    assert verdicts(out, "x1_") == {"x1_forcerun_runs": "as_predicted", "x1_setrun_walks": "as_predicted",
                                    "x1_autowalk_runs": "as_predicted", "x1_autowalk_heads": "as_predicted",
                                    "x1_forcerun_tick": "recorded", "x1_once_holds": "as_predicted",
                                    "x1_endurance": "as_predicted"}
    assert out["verdicts"]["x1_forcerun_runs"]["predicted"] == D.PREDICTIONS["x1_forcerun_runs"]
    # X3
    ld = rd["load"]
    assert ld["server_arm"]["hooked"] is True and ld["client_arm"]["hooked"] is True
    assert ld["before"]["weight"] == FakeModP.LOAD0 and ld["planks_added"] == 4 and ld["level3_at_add"] == 4
    assert ld["level3_at_ratio"] == pytest.approx(13 / 8) and [a["level"] for a in ld["adds"]] == [0, 0, 2, 3]
    assert ld["drop"]["k"] == 1 and ld["drop"]["predicted_ratio"] == pytest.approx(1.25)
    assert ld["drop"]["goal"]["detail"] == "moved=1" and ld["drop"]["after"]["level"] == 2
    assert ("client", "event.watch", "OnPlayerGetDamage read") in [c for c in calls]
    assert ("server", "fall.probe", "admin") in calls and not [c for c in calls if c[1] == "inventory.add"]
    assert [c[1:] for c in calls if c[0] == "rcon"] == [('additem "admin" "Base.Plank" 1', "add_%d" % i)
                                                         for i in range(1, 5)]
    assert all(a["weight_rose"] and a["rcon"]["ok"] for a in ld["adds"]) and "load_stalled_at" not in ld
    assert ld["walk_loaded"] and ld["walk_level2"] and all(r["arm"] == "walk_loaded" for r in ld["walk_loaded"])
    assert ld["floor_reached"]["arm"] == "walk_loaded"
    tr = ld["trace"]
    assert tr and set(tr[0]) == {"seq", "wallMs", "health", "level", "weight", "moving", "action"}
    assert ld["drops"] and all(d["level"] >= 3 for d in ld["drops"])
    # the fake drops on a moving frame; the reading carries the frame before's moving, false on a leg's first frame
    assert len([d for d in ld["drops"] if d["moving"] is not True]) <= len(ld["walk_loaded"])
    assert min(r["health"] for r in tr) <= 75 and ld["damage_events"] == []
    assert verdicts(out, "x3_") == {"x3_drops_at_level3_only": "as_predicted", "x3_floor_75": "as_predicted",
                                    "x3_drops_while_still": "recorded", "x3_level2_no_drop": "as_predicted",
                                    "x3_server_hears_heavyload": "as_predicted",
                                    "x3_client_hears_heavyload": "as_predicted",
                                    "x3_level3_at_ratio": "as_predicted"}
    assert out["verdicts"]["x3_drops_while_still"]["observed"]["drops"] == 0
    assert out["verdicts"]["x3_client_hears_heavyload"]["predicted"] == 0
    # server, the fold
    assert len(rd["server"]) == 1 and rd["server"][0]["ack"]["ok"]
    assert out["frames_n"] > 100 and out["gaps"] == [] and out["bad"] == 0 and out["lua_errors"] == 0
    assert (probe.xs.path and os.path.isfile(probe.xs.path))
    s = D.summary(out)
    assert s["paces"]["forcerun"] == pytest.approx(3.2) and s["bench_median_us"]["poll"] == 150.0
    assert set(s["x3"]) == set(verdicts(out, "x3_"))


def test_a_forcerun_that_walks_fails_and_runs_the_toggle_legs(tmp_path):
    probe, out, mod, _ = make_probe(tmp_path, forcerun_runs=False)
    run_phases(probe, ["hello_and_map", "x1_motor"])
    assert out["phase_errors"] == {}
    m = out["readings"]["motor"]
    assert len(m["toggle"]) == D.TOGGLE_LEGS and "toggle_skipped" not in m
    assert all(r["arm"] == "toggle" and r["pace"] == pytest.approx(3.2) for r in m["toggle"])
    assert any(c["args"].endswith(" toggle") for c in mod.cmds if c["goal"] == "goto")
    v = verdicts(out, "x1_")
    assert v["x1_forcerun_runs"] == "falsified" and v["x1_autowalk_runs"] == "falsified"
    assert v["x1_setrun_walks"] == "as_predicted"


def test_a_twenty_degree_autowalk_heading_fails_the_heads_grade(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "AUTOWALK_LEGS", SHORT_AUTOWALK)
    probe, out, _, _ = make_probe(tmp_path, heading_err=20.0)
    run_phases(probe, ["hello_and_map", "x1_motor"])
    v = out["verdicts"]["x1_autowalk_heads"]
    assert v["verdict"] == "falsified" and v["observed"]["max"] == pytest.approx(20.0)


def test_a_once_that_does_not_hold_fails(tmp_path):
    probe, out, _, _ = make_probe(tmp_path, once_holds=False)
    run_phases(probe, ["hello_and_map", "x1_motor"])
    assert out["verdicts"]["x1_once_holds"]["verdict"] == "falsified"
    assert out["verdicts"]["x1_once_holds"]["observed"]["updForceRun"] == 0


def test_a_drop_at_level_two_fails_the_level3_grade(tmp_path):
    probe, out, _, _ = make_probe(tmp_path, drop_level=2, drop_every=50)
    run_phases(probe, ["hello_and_map", "x3_load"])
    assert out["phase_errors"] == {}
    v = verdicts(out, "x3_")
    assert v["x3_drops_at_level3_only"] == "falsified" and v["x3_level2_no_drop"] == "falsified"


def test_a_drain_past_the_floor_fails_floor_75(tmp_path):
    probe, out, _, _ = make_probe(tmp_path, floor=False)
    run_phases(probe, ["hello_and_map", "x3_load"])
    v = out["verdicts"]["x3_floor_75"]
    assert v["verdict"] == "falsified" and v["observed"]["from_at_or_below_floor"] > 0


def test_a_client_that_hears_falsifies_the_client_grade(tmp_path):
    probe, out, mod, _ = make_probe(tmp_path, client_hears=True)
    run_phases(probe, ["hello_and_map", "x3_load"])
    v = out["verdicts"]["x3_client_hears_heavyload"]
    assert v["verdict"] == "falsified" and v["observed"]["event_watch_count"] == mod.client_count > 0
    assert v["observed"]["damage_events_heavyload"] == mod.client_count
    ev = out["readings"]["load"]["damage_events"]
    assert ev[0]["tag"] == "HEAVYLOAD" and ev[0]["isLocal"] is True and ev[0]["amount"] == FakeModP.DROP


def test_server_counts_without_heavyload_fail_the_server_grade(tmp_path):
    probe, out, _, _ = make_probe(tmp_path, server_heavy=False)
    run_phases(probe, ["hello_and_map", "x3_load"])
    assert out["verdicts"]["x3_server_hears_heavyload"]["verdict"] == "falsified"


def test_an_old_hello_aborts_the_later_phases(tmp_path):
    probe, out, mod, calls = make_probe(tmp_path, version="0.1")
    probe.run()
    assert out["abort"] == "Lua 0.1: the probe mod did not load" and out["phase_errors"] == {}
    rd = out["readings"]
    assert rd["bench"] == {} and rd["motor"] == {} and rd["load"] == {} and rd["server"] == [] and rd["line"] is None
    assert calls == [] and not [c for c in mod.cmds if c["goal"] in ("goto", "scan", "autowalk")]
    assert sum("skipped" in n["note"] for n in out["notes"]) == 4


def test_a_bench_error_reply_is_kept_as_a_row_and_the_phase_completes(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "BENCH_ARMS", D.BENCH_ARMS + [("nonDict", 5)])
    probe, out, _, _ = make_probe(tmp_path, bench_error=("heldWrite",))
    run_phases(probe, ["hello_and_map", "x2_bench"])
    assert out["phase_errors"] == {}
    rows = out["readings"]["bench"]["rows"]
    bad = [r for r in rows if r["arm"] == "heldWrite"]
    assert len(bad) == 3 and all(r["error"].startswith("attempted index") and r["usPerCall"] is None for r in bad)
    nd = [r for r in rows if r["arm"] == "nonDict"]
    assert len(nd) == 3 and all(r["error"].startswith("non-dict reply") for r in nd)
    s = out["readings"]["bench"]["summary"]
    assert s["heldWrite"]["median_usPerCall"] is None and s["heldWrite"]["us_per_kb"] is None
    assert s["json"]["reps"] == 3 and s["heldWrite"]["reps"] == 0


def test_the_budget_stops_a_phase_and_is_recorded(tmp_path):
    probe, out, _, _ = make_probe(tmp_path, budget_s=40.0)
    probe.run()
    assert "budget_stop" in out["phase_walls"]["x1_motor"] and "budget_stop" not in out["phase_walls"]["x2_bench"]
    assert out["budget_stop"]["phase"] == "x3_load"                  # xs keeps the last phase's stop
    assert out["readings"]["bench"]["summary"]                       # the bench ran before the budget
    assert out["verdicts"]["x1_forcerun_runs"]["verdict"] == "unmeasured"     # graded in the phase's finally
    assert "budget_stop" in out["phase_walls"]["x3_load"]
    assert len(out["readings"]["server"]) == 1                       # the server phase has no poll, so it runs
    # the readback never ran: no counts, no drops, so every X3 grade but the recorded one reads unmeasured
    v = verdicts(out, "x3_")
    assert v.pop("x3_drops_while_still") == "recorded" and set(v.values()) == {"unmeasured"}, v


def test_no_open_line_falls_back_to_the_pass4_leg(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "choose_line", lambda squares, me, z=0, n=12: None)
    probe, out, _, _ = make_probe(tmp_path)
    run_phases(probe, ["hello_and_map"])
    line = out["readings"]["line"]
    assert line["fallback"] == "pass 4 legs" and line["bx"] == line["ax"] + D.FALLBACK_DX and line["by"] == line["ay"]
    assert probe.line["B"] == (line["ax"] + 10, line["ay"])


def test_a_setrun_that_runs_and_a_flat_endurance_fail_their_grades(tmp_path):
    probe, out, _, _ = make_probe(tmp_path, setrun_runs=True, endurance_flat=True)
    run_phases(probe, ["hello_and_map", "x1_motor"])
    v = verdicts(out, "x1_")
    assert v["x1_setrun_walks"] == "falsified" and v["x1_endurance"] == "falsified"
    assert out["verdicts"]["x1_setrun_walks"]["observed"]["ratio"] == pytest.approx(2.0)
    assert v["x1_forcerun_runs"] == "as_predicted"


def test_level_three_below_a_ratio_of_one_and_a_half_fails_the_ratio_grade(tmp_path):
    probe, out, _, _ = make_probe(tmp_path, level3_from=1.2)
    run_phases(probe, ["hello_and_map", "x3_load"])
    v = out["verdicts"]["x3_level3_at_ratio"]
    assert v["verdict"] == "falsified" and v["observed"]["level3_at_ratio"] == pytest.approx(10 / 8)


def test_a_load_that_never_reaches_level_three_reads_unmeasured(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "LOAD_MAX_ADDS", 2)
    probe, out, _, _ = make_probe(tmp_path)
    run_phases(probe, ["hello_and_map", "x3_load"])
    ld = out["readings"]["load"]
    assert "level3_at_ratio" not in ld and ld["level_reached"] == 0 and len(ld["adds"]) == 2
    v = verdicts(out, "x3_")
    assert v["x3_level3_at_ratio"] == "unmeasured" and v["x3_drops_at_level3_only"] == "unmeasured"


def test_the_probes_autowalk_legs_stay_on_the_strip_and_a_faster_run_voids(tmp_path):
    probe, out, _, _ = make_probe(tmp_path)
    run_phases(probe, ["hello_and_map", "x1_motor"])
    aw = out["readings"]["motor"]["autowalk"]
    assert len(aw) == 6 and not any(r["voided"] for r in aw) and all(r["off_strip_frames"] == 0 for r in aw)
    assert verdicts(out, "x1_")["x1_autowalk_runs"] == "as_predicted"
    probe, out, _, _ = make_probe(tmp_path / "fast", run_tps=5.5)   # 8.25 tiles in 1.5 s: past the 7 tiles ahead
    run_phases(probe, ["hello_and_map", "x1_motor"])
    aw = out["readings"]["motor"]["autowalk"]
    assert [r["voided"] for r in aw] == [None] + ["left the strip"] * 4 + [None], [r["voided"] for r in aw]
    assert all(r["pace"] == pytest.approx(5.5) and r["heading_error_deg"] is not None for r in aw[1:5])   # kept
    v = verdicts(out, "x1_")
    # a voided leg is out of every sample: the runs and the once leg read unmeasured, the two walks still head
    assert v["x1_autowalk_runs"] == v["x1_once_holds"] == "unmeasured" and v["x1_autowalk_heads"] == "as_predicted"
    assert out["verdicts"]["x1_autowalk_heads"]["observed"]["voided_legs"] == 4


def test_the_autowalk_vector_follows_a_minus_x_line(tmp_path):
    probe, out, mod, _ = make_probe(tmp_path, blocked={(101, 200)})
    run_phases(probe, ["hello_and_map", "x1_motor"])
    line = out["readings"]["line"]
    assert (line["ax"], line["ay"], line["bx"], line["by"], line["dir"]) == (100, 200, 89, 200, "-x")
    assert [c["args"] for c in mod.cmds if c["goal"] == "autowalk"] == [
        "-0.707107 -0.707107 1.5", "-0.707107 -0.707107 3.0", "0.707107 0.707107 1.5 forcerun",
        "-1.414214 -1.414214 1.5 forcerun", "1.378858 1.378858 1.5 once", "-0.707107 -0.707107 1.5 forcerun",
        "0.707107 0.707107 3.0"]
    aw = out["readings"]["motor"]["autowalk"]
    assert [(r["vx"], r["vy"]) for r in aw][:2] == [(-1.0, 0.0), (1.0, 0.0)] and not any(r["voided"] for r in aw)
    assert verdicts(out, "x1_")["x1_autowalk_heads"] == "as_predicted"


def test_axis_vectors_and_strips():
    assert D.axis_vector("+x", 1, 0) == (1.0, 0.0) and D.axis_vector("-x", -1.95, 0) == (1.95, 0.0)
    assert D.axis_vector("+y", 2, 0) == (0.0, 2.0) and D.axis_vector("-y", 1, 0) == (0.0, -1.0)
    assert D.axis_vector("+x", 0, 1) == (0.0, 1.0)                        # dy: across the axis
    assert [D._arg(v) for v in (1.0, -1.0, -1.95, -0.0, 0.0, 2)] == ["1", "-1", "-1.95", "0", "0", "2"]
    st = D.strip_of(10, 20, "+y", 12)
    assert len(st) == 36 and (9, 20) in st and (11, 31) in st and (10, 32) not in st and (12, 20) not in st
    assert D.strip_of(5, 5, "-x", 3) == {(x, y) for x in (3, 4, 5) for y in (4, 5, 6)}
    fr = [{"x": 10.2, "y": 20.9}, {"x": 11.99, "y": 31.5}, {"x": 12.0, "y": 25.0}]
    assert D.off_strip(fr, st) == [fr[2]]


def test_a_stalled_load_stops_at_once_and_x3_reads_unmeasured(tmp_path):
    probe, out, _, calls = make_probe(tmp_path, stall=True)
    run_phases(probe, ["hello_and_map", "x3_load"])
    ld = out["readings"]["load"]
    assert ld["load_stalled_at"] == 1 and len(ld["adds"]) == 1 and ld["adds"][0]["weight_rose"] is False
    assert ld["load_stalled_reply"]["ok"] is True and ld["planks_added"] == 0 and ld["level_reached"] == 0
    assert len([c for c in calls if c[0] == "rcon"]) == 1
    assert ld["drop"]["error"] == "no plank added: nothing to drop"
    v = verdicts(out, "x3_")
    assert v.pop("x3_drops_while_still") == "recorded" and set(v.values()) == {"unmeasured"}, v


@pytest.mark.parametrize("flags, unmeasured", [
    ({"drop_level": 9}, {"x3_server_hears_heavyload", "x3_client_hears_heavyload", "x3_drops_at_level3_only",
                         "x3_floor_75"}),
    ({"drop_every": 40}, {"x3_floor_75"})])
def test_x3_grades_without_their_evidence_read_unmeasured(tmp_path, flags, unmeasured):
    probe, out, mod, _ = make_probe(tmp_path, **flags)
    run_phases(probe, ["hello_and_map", "x3_load"])
    v = verdicts(out, "x3_")
    assert {k for k, x in v.items() if x == "unmeasured"} == unmeasured, v
    assert "falsified" not in v.values()
    if "drop_every" in flags:
        assert 0 < mod.drops and mod.health > D.HEALTH_FLOOR and v["x3_server_hears_heavyload"] == "as_predicted"


def test_the_x1_deadline_skips_the_remaining_legs(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "X1_DEADLINE_S", 40.0)
    probe, out, mod, _ = make_probe(tmp_path)
    run_phases(probe, ["hello_and_map", "x1_motor", "x3_load"])
    m = out["readings"]["motor"]
    sk = [r for r in m["legs"] + m["autowalk"] if r.get("skipped")]
    assert sk and all(r["skipped"] == "x1 deadline" for r in sk) and m["return"]["skipped"] == "x1 deadline"
    assert all(r["skipped"] == "x1 deadline" for r in m["centre"]) and len(m["centre"]) == 7
    assert len(m["legs"]) == 15 and len(m["autowalk"]) == 6
    assert m["autowalk_calibration"]["skipped"] == "x1 deadline" and m["autowalk_correction_deg"] == 0
    assert m["deadline_skipped"] == len(sk) + 7 + 1 + 1
    assert m["rate_back"]["ack"]["ok"] and mod.rate == 5
    assert out["phase_errors"] == {} and "budget_stop" not in out
    assert out["readings"]["load"]["level3_at_add"] == 4                # X3 still had its wall
    assert len([c for c in mod.cmds if c["goal"] == "autowalk"]) == 0


def test_input_vectors_follow_the_engines_mapping():
    for wx, wy in ((1, 0), (-1.95, 0), (0, 2), (0.6, -0.8)):
        ix, iy = D.input_vector(wx, wy)
        r2 = math.sqrt(2)
        # the engine's world vector (iy + ix, iy - ix) is the wanted one scaled by sqrt 2 (an input length kept)
        assert (iy + ix, iy - ix) == (pytest.approx(wx * r2, abs=1e-5), pytest.approx(wy * r2, abs=1e-5))
    assert D.input_vector(1, 0) == (0.707107, 0.707107) and D.input_vector(0, 0) == (0.0, 0.0)
    assert D.input_vector(1, 0, -45.0) == (1.0, 0.0)
    # only a +-45 deg snap is applied (a 90 or 180 reading is a deflected leg), and none under 1 tile of movement
    assert [D.correction_of(a) for a in (None, 0.0, 15.0, 20.0, 30.0, 45.0, -50.0, 100.0, 180.0)] == [
        0.0, 0.0, 0.0, 0.0, -45.0, -45.0, 45.0, 0.0, 0.0]
    assert D.correction_of(45.0, 0.6) == 0.0 and D.correction_of(45.0, 1.0) == -45.0 and D.CALIBRATE_MIN_TILES == 1.0
    fr = [{"x": 0, "y": 0}, {"x": 1, "y": 1}]
    assert D.heading_signed_deg(fr, 1, 0) == pytest.approx(45) and D.heading_signed_deg(fr, 0, 1) == pytest.approx(-45)
    assert D.heading_signed_deg(fr, -1, -1) == pytest.approx(180) and D.heading_signed_deg(fr[:1], 1, 0) is None


def test_a_fake_without_the_engines_transform_is_corrected_by_minus_45(tmp_path):
    # identity mapping: the wanted world (1, 0) sent as (0.707107, 0.707107) walks at +45 deg (counter-clockwise in
    # world x, y), so the snapped correction is -45 deg and every later leg is sent rotated by it
    probe, out, mod, _ = make_probe(tmp_path, mapping="identity")
    run_phases(probe, ["hello_and_map", "x1_motor"])
    m = out["readings"]["motor"]
    assert m["autowalk_calibration"]["heading_signed_deg"] == pytest.approx(45.0, abs=0.5)
    assert m["autowalk_correction_deg"] == -45.0
    aw = m["autowalk"]
    assert all(r["correction_deg"] == -45.0 for r in aw) and (aw[0]["ix"], aw[0]["iy"]) == (1.0, 0.0)
    assert all(r["heading_error_deg"] <= D.CALIBRATE_TOL_DEG for r in aw) and not any(r["voided"] for r in aw)
    assert verdicts(out, "x1_")["x1_autowalk_heads"] == "as_predicted"
    # the engine's mapping reads no correction (the clean run asserts 0 too)
    probe, out, _, _ = make_probe(tmp_path / "engine")
    run_phases(probe, ["hello_and_map", "x1_motor"])
    assert out["readings"]["motor"]["autowalk_correction_deg"] == 0
