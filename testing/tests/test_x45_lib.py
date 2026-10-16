"""Offline tests of testing/experiments/x45_lib.py (Plan 15 Task 2, run x451): every grade with a failing case and its
unmeasured case, the pre-boot checks on the real repository, a real run layout and a real staged copy of the pinned
commit, and the session's body run (S to K, then E) against a fake world behind a fake bus, once as predicted and once
per defect flag that must move a named grade off as_predicted.

The fake bus answers the harness's real reply shapes, read off the handlers' `@reply` lines
(docs/reference/harness-commands.md): witness.chain {ok, value, hops, failedAt} with the end value tostring'd (a void
setter "nil", a table walked one level into strings); health.get {ok, side, overall, health, parts}; stats.get {...,
weight, hunger, thirst, moodles {hungry, thirst, ...}, worldAge, mult, wall}; stats.set and nutrition.set the
post-write snapshot {..., weight, hunger, thirst [, applied]}; stats.setany {ok, stat, side, requested, before, after};
moodle.level {ok, side, user, moodle, level}; fall.probe {ok, side, hooked, fall, counts, legs, maxFracture} (an empty
counts table encodes as a list); bodypart.set {ok, side, part, field, requested, before, after, synced}; lua.setpath
{ok, side, path, before, after}; lua.read {ok, side, root, n, values, tables, types, missing}; foodtimer.set
{requested, before, set, after}; moddata.set {user, key, value, side, keyCount, keys, serverWorldAge}; autodrink.probe
{ok, side, thirst, autoDrink, containers}; time.snapshot {worldAge, hour, minutes, mult, trueMult, wall}; players a
list of usernames.
"""
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x45_lib as L                   # noqa: E402
import xlib as X                      # noqa: E402

REPO = L.REPO


def fresh_out():
    return {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
            "world_changes": {"left_in_place": []}}


# ---------------------------------------------------------------- the fake world
class Clock:
    def __init__(self, world):
        self.t = 1000.0
        self.world = world

    def __call__(self):
        return self.t

    def sleep(self, dt):
        self.world.sleeps += 1
        if "thirst_drop" in self.world.f and self.world.hunger > 0.70 and self.world.sleeps_high is None:
            self.world.sleeps_high = self.world.sleeps
        if self.world.sleeps_high is not None and self.world.sleeps == self.world.sleeps_high + 10:
            self.world.thirst = 0.5
        self.world.advance(dt)


class World:
    """One character on a DayLength-1 server at speed 1: a game hour is 37.5 wall s, 10 ticks a wall s, the
    multiplier summing to 1800 a game hour. Each bus step takes STEP_S of wall time."""
    STEP_S = 0.5
    GH_S = 37.5
    TPS = 10.0
    BLEED_PER_GH = 2.0         # the per-part wound term a game hour per unit of bleedingTime (made up, any > 0)

    def __init__(self, flags=()):
        self.f = set(flags)
        self.red = L.CONST_DEFAULT
        self.hunger, self.thirst = 0.2, 0.01
        self.food_sick = 0.0
        self.parts = {}            # index -> [bleedingTime, flag]
        self.health = 100.0
        self.age = 10.0
        self.mode = 1
        self.moddata = {}
        self.saved_moddata = {}
        self.weight = 80.0
        self.counts = {}
        self.clock = Clock(self)
        self.n_steps = 0
        self.sleeps = 0
        self.sleeps_high = None

    # -- the engine
    def mult_tick(self):
        return 1800.0 / (self.GH_S * self.TPS)

    def red_for(self, term):
        if "red_ignored" in self.f:
            return L.CONST_DEFAULT
        if term == "SICK" and "sick_free" in self.f:
            return L.CONST_DEFAULT
        return self.red

    def levels(self):
        bleeding = sum(1 for t, fl in self.parts.values() if fl and t > 0)
        return {"hungry": 4 if self.hunger > 0.70 else 0, "thirst": 4 if self.thirst > 0.84 else 0,
                "SICK": 4 if self.food_sick / 100.0 > 0.90 else 0, "BLEEDING": min(4, bleeding)}

    def advance(self, dt):
        lv = self.levels()
        gh = dt / self.GH_S
        ticks = int(round(dt * self.TPS))
        k_h = 2.0 if "rate_x2" in self.f else 1.0
        terms = {"HUNGRY": (lv["hungry"] == 4, self.red_for("HUNGRY") * L.K_HUNGRY * k_h),
                 "THIRST": (lv["thirst"] == 4, self.red_for("THIRST") * L.K_THIRST * k_h),
                 "SICK": (lv["SICK"] == 4, self.red_for("SICK") * L.K_SICK),
                 "BLEEDING4": (lv["BLEEDING"] == 4, self.red_for("BLEEDING") * L.K_BLEEDING)}
        drop = 0.0
        for tag, (on, per_mult) in terms.items():
            if on and per_mult > 0:
                drop += per_mult * 1800.0 * gh
                t = "BLEEDING" if tag == "BLEEDING4" else tag
                self.counts[t] = self.counts.get(t, 0) + ticks
        bt = sum(t for t, fl in self.parts.values() if fl and t > 0)
        if bt > 0:
            scale = (self.red / L.CONST_DEFAULT) if "bleed_needs_red" in self.f else 1.0
            if scale > 0:
                drop += self.BLEED_PER_GH * bt * gh * scale
                self.counts["BLEEDING"] = self.counts.get("BLEEDING", 0) + ticks
        self.health = max(0.0, self.health - drop)
        self.age += gh
        self.clock.t += dt
        if self.mode == 1 or "no_mode" in self.f:
            self.hunger = min(self.hunger, 0.69)
            self.thirst = min(self.thirst, 0.83)

    # -- the bus
    def snap(self):
        lv = self.levels()
        return {"calories": 800, "weight": self.weight, "hunger": self.hunger, "thirst": self.thirst,
                "moodles": {"hungry": lv["hungry"], "thirst": lv["thirst"], "foodEaten": 0, "heavyLoad": 0,
                            "endurance": 0},
                "worldAge": self.age, "mult": self.mult_tick(), "wall": int(self.clock.t * 1000)}

    def ask(self, node, cmd, args="", timeout=30):
        self.n_steps += 1
        self.advance(self.STEP_S / 2)
        r = self._answer(cmd, args.split() if args else [])
        self.advance(self.STEP_S / 2)
        return r

    def _answer(self, cmd, a):
        if cmd == "players":
            return ["admin"]
        if cmd == "ping":
            return "pong"
        if cmd == "time.snapshot":
            return {"worldAge": self.age, "hour": 10, "minutes": 0, "mult": self.mult_tick(), "trueMult": 1,
                    "wall": int(self.clock.t * 1000)}
        if cmd == "witness.chain":
            chain = a[1]
            if chain == L.GET_CHAIN:
                return {"ok": True, "value": repr(self.red), "hops": 2}
            if chain.startswith("getBodyDamage.setHealthReductionFromSevereBadMoodles("):
                v = float(chain[chain.index("(") + 1:-1])
                if "setter_inert" not in self.f:
                    self.red = v
                return {"ok": True, "value": "nil", "hops": 2}
            if chain == "getModData":
                return {"ok": True, "value": {k: str(v) for k, v in self.moddata.items()}, "hops": 1}
            return {"ok": False, "failedAt": 1, "error": "no member", "hops": 1}
        if cmd == "lua.read":
            return {"ok": True, "side": "server", "root": "_G", "n": 3, "missing": {}, "types": {}, "tables": {},
                    "values": {L.MODE_PATH: self.mode, "SandboxVars.DayLength": 1, "SandboxVars.Nutrition": False}}
        if cmd == "lua.setpath":
            before = self.mode
            self.mode = int(float(a[1]))
            return {"ok": True, "side": "server", "path": a[0], "before": before, "after": self.mode}
        if cmd == "health.get":
            return {"ok": True, "side": "server", "overall": self.health, "health": self.health, "parts": []}
        if cmd == "autodrink.probe":
            return {"ok": True, "side": "server", "containers": 0, "thirst": self.thirst, "autoDrink": True}
        if cmd == "foodtimer.set":
            return {"requested": 0, "before": 0, "set": True, "after": 0}
        if cmd == "fall.probe":
            return {"ok": True, "side": "server", "hooked": True, "fall": [],
                    "counts": dict(self.counts) if self.counts else [], "legs": [], "maxFracture": 0}
        if cmd == "stats.set":
            for i in range(1, len(a) - 1, 2):
                setattr(self, a[i], float(a[i + 1]))
            if self.mode == 1 or "no_mode" in self.f:
                self.hunger, self.thirst = min(self.hunger, 0.69), min(self.thirst, 0.83)
            return dict(self.snap(), applied={"hunger": "Stats"})
        if cmd == "stats.get":
            return self.snap()
        if cmd == "stats.setany":
            before = self.food_sick
            self.food_sick = float(a[2])
            return {"ok": True, "stat": a[1], "side": "server", "requested": float(a[2]), "before": before,
                    "after": self.food_sick}
        if cmd == "moodle.level":
            return {"ok": True, "side": "server", "user": a[0], "moodle": a[1], "level": self.levels()[a[1]]}
        if cmd == "bodypart.set":
            i, field, raw = int(a[1]), a[2], a[3]
            p = self.parts.setdefault(i, [0.0, False])
            if field == "bleedingTime":
                p[0] = float(raw)
            else:
                p[1] = raw == "true"
            return {"ok": True, "side": "server", "part": i, "field": field, "requested": raw, "after": raw,
                    "synced": False}
        if cmd == "nutrition.set":
            w = float(a[2])
            if w < 35.0:
                w = 35.0
                red = L.CONST_DEFAULT if "lw_always" in self.f else self.red
                if "lw_free" not in self.f:
                    self.health -= red * self.mult_tick()
            self.weight = w
            return self.snap()
        if cmd == "moddata.set":
            self.moddata[a[1]] = a[2]
            return {"user": a[0], "key": a[1], "value": a[2], "side": "server", "keyCount": len(self.moddata),
                    "keys": list(self.moddata), "serverWorldAge": self.age}
        return {"error": f"fake: unknown {cmd}"}

    def reboot(self):
        """The reuse boot: the constant back to the constructor's unless the defect keeps it; modData and health kept."""
        if "saved" not in self.f:
            self.red = L.CONST_DEFAULT
        if "fresh_char" in self.f:
            self.moddata = {}
            self.health = 100.0
        self.mode = 1


class FakeClient:
    def __init__(self, user):
        self.username = user
        self.seen = {}
        self.alive = True
        self.console = os.devnull


def run(flags=(), budget=1e9, with_e=True):
    w = World(flags)
    out = fresh_out()
    xs = X.Xs(out, node=lambda side: side, clients={"admin": FakeClient("admin")}, ask=w.ask, budget_s=budget,
              clock=w.clock, sleep=w.clock.sleep, user="admin")
    S = L.Sess(xs)
    S.body_run()
    if with_e:
        w.reboot()
        S.phase_E()
    out["logs"] = {"mod_error": {"server-stdout.log": []}}
    out["admin_lua_error"] = False
    S.grade_all()
    return {k: v["verdict"] for k, v in out["verdicts"].items()}, out, w


# ---------------------------------------------------------------- the body run against the fake world
def test_as_predicted_end_to_end():
    v, out, w = run()
    assert v == {k: "as_predicted" for k in v}, {k: (x, out["verdicts"][k]["observed"]) for k, x in v.items()
                                                 if x != "as_predicted"}
    for k in ("ROUTE_B_const", "ROUTE_D_const", "ROUTE_K_const", "A", "LW_A", "B", "LW_B", "C1", "C2", "D", "E", "Z"):
        assert k in v
    assert w.mode == 1 and w.red == L.CONST_DEFAULT


@pytest.mark.parametrize("flag,grades", [
    ("red_ignored", {"B", "C1", "LW_B"}),
    ("sick_free", {"C1"}),
    ("bleed_needs_red", {"C2"}),
    ("rate_x2", {"A"}),
    ("setter_inert", {"ROUTE_B_const", "ROUTE_K_const", "B"}),
    ("saved", {"E"}),
    ("lw_free", {"LW_A"}),
    ("lw_always", {"LW_B"}),
])
def test_each_defect_moves_its_grade(flag, grades):
    v, out, _ = run((flag,))
    for gname in grades:
        assert v[gname] != "as_predicted", (flag, gname, out["verdicts"][gname]["observed"])


def test_mod_rewriting_hunger_leaves_the_windows_unmeasured():
    v, _, _ = run(("no_mode",))
    assert v["A"] == "unmeasured" and v["B"] == "unmeasured"


def test_a_thirst_drop_mid_window_unmeasures_a():
    v, _, _ = run(("thirst_drop",))
    assert v["A"] == "unmeasured"


def test_a_fresh_character_after_the_reload_unmeasures_e():
    v, _, _ = run(("fresh_char",))
    assert v["E"] == "unmeasured"


def test_no_e_without_the_reload():
    v, _, _ = run(with_e=False)
    assert "E" not in v


def test_a_dead_start_skips_to_the_cleanup():
    w = World()
    w.mode = 2
    out = fresh_out()
    xs = X.Xs(out, node=lambda side: side, clients={}, ask=w.ask, clock=w.clock, sleep=w.clock.sleep)
    S = L.Sess(xs)
    S.body_run()
    assert "S" in out["phase_errors"] and out["skipped_phases"] == ["A", "B", "C1", "C2", "D"]
    assert "K" in out["phase_walls"] and w.mode == 2      # restored to the value S read, never a constant


def test_the_budget_stops_the_drain_phases():
    v, out, _ = run(budget=60.0, with_e=False)
    assert out.get("budget_stop") and "K" in out["phase_walls"]
    assert v.get("D", "unmeasured") != "as_predicted" or "D" not in v


# ---------------------------------------------------------------- the pure grades: failing and unmeasured cases
def _w(dh=-1.0, dwall=20.0, gh=20.0 / 37.5, lv=4, sick=4, bleed=4, c0=None, c1=None):
    s0 = {"worldAge": 10.0, "moodles": {"hungry": lv, "thirst": lv}, "wall": 0, "wall_after": 0.5}
    s1 = {"worldAge": 10.0 + gh, "moodles": {"hungry": lv, "thirst": lv}, "wall": dwall, "wall_after": dwall + 0.5}
    lvs = {"SICK": {"level": sick}, "BLEEDING": {"level": bleed}}
    return {"h0": {"overall": 99.0, "wall": 0.0, "wall_after": 0.0}, "h1": {"overall": 99.0 + dh, "wall": dwall,
                                                                             "wall_after": dwall},
            "s0": s0, "s1": s1, "lv0": lvs, "lv1": lvs, "c0": c0 if c0 is not None else {"counts": {}},
            "c1": c1 if c1 is not None else {"counts": {}}}


def test_window_rate():
    r = L.window_rate(_w(dh=-1.0, dwall=37.5, gh=1.0))
    assert abs(r["rate_per_gh"] - 1.0) < 1e-9
    assert L.window_rate({"h0": {}, "h1": {}})["rate_per_gh"] is None


def test_grade_control():
    pred = L.CONST_DEFAULT * 1800 * (L.K_HUNGRY + L.K_THIRST)
    assert L.grade_control(_w(dh=-pred, dwall=37.5, gh=1.0), L.CONST_DEFAULT, 1)[0] == "as_predicted"
    assert L.grade_control(_w(dh=-pred * 1.2, dwall=37.5, gh=1.0), L.CONST_DEFAULT, 1)[0] == "falsified"
    assert L.grade_control(_w(dh=-pred, dwall=37.5, gh=1.0, lv=3), L.CONST_DEFAULT, 1)[0] == "unmeasured"


def test_grade_hold():
    c = {"counts": {"HUNGRY": 5}}
    assert L.grade_hold(_w(dh=0.0, c0=c, c1=c), ("hungry",), ("HUNGRY",))[0] == "as_predicted"
    assert L.grade_hold(_w(dh=-0.05, c0=c, c1=c), ("hungry",), ("HUNGRY",))[0] == "falsified"
    assert L.grade_hold(_w(dh=0.0, c0=c, c1={"counts": {"HUNGRY": 6}}), ("hungry",), ("HUNGRY",))[0] == "falsified"
    assert L.grade_hold(_w(dh=0.0, c0=c, c1=c, sick=2), ("SICK",), ("SICK",))[0] == "unmeasured"
    assert L.grade_hold(_w(dh=0.0, c0={}, c1=c), ("hungry",), ("HUNGRY",))[0] == "unmeasured"


def test_grade_bleed():
    want = ("hungry", "BLEEDING")
    assert L.grade_bleed(_w(dh=-1.0, c1={"counts": {"BLEEDING": 9}}), want)[0] == "as_predicted"
    assert L.grade_bleed(_w(dh=-0.01, c1={"counts": {"BLEEDING": 9}}), want)[0] == "falsified"
    assert L.grade_bleed(_w(dh=-1.0), want)[0] == "falsified"
    assert L.grade_bleed(_w(dh=-1.0, c1={"counts": {"BLEEDING": 9, "SICK": 1}}), want)[0] == "falsified"
    assert L.grade_bleed(_w(dh=-1.0, bleed=3, c1={"counts": {"BLEEDING": 9}}), want)[0] == "unmeasured"


def test_grade_restore():
    k = L.K_HUNGRY + L.K_THIRST + L.K_SICK + L.K_BLEEDING
    pred = L.CONST_DEFAULT * 1800 * k
    tags = {"counts": {"HUNGRY": 1, "THIRST": 1, "SICK": 1}}
    wc2 = _w(dh=-2.0, dwall=37.5, gh=1.0)
    wd = _w(dh=-(2.0 + pred), dwall=37.5, gh=1.0, c1=tags)
    assert L.grade_restore(wd, wc2, L.CONST_DEFAULT, 1)[0] == "as_predicted"
    assert L.grade_restore(_w(dh=-(2.0 + pred * 0.5), dwall=37.5, gh=1.0, c1=tags), wc2, L.CONST_DEFAULT,
                           1)[0] == "falsified"
    assert L.grade_restore(_w(dh=-(2.0 + pred), dwall=37.5, gh=1.0), wc2, L.CONST_DEFAULT, 1)[0] == "falsified"
    assert L.grade_restore(wd, {"h0": {}, "h1": {}}, L.CONST_DEFAULT, 1)[0] == "unmeasured"


def _br(drop, calls=5, weight=35.0, mult=4.8):
    return {"h0": {"overall": 90.0, "wall": 0.0, "wall_after": 0.0},
            "h1": {"overall": 90.0 - drop, "wall": 3.0, "wall_after": 3.0},
            "s": {"mult": mult}, "calls": [{"weight": weight}] * calls}


def test_grade_lowweight():
    pred = 5 * L.CONST_DEFAULT * 4.8
    assert L.grade_lowweight(_br(pred), 0.0, L.CONST_DEFAULT, True)[0] == "as_predicted"
    assert L.grade_lowweight(_br(0.0), 0.0, L.CONST_DEFAULT, True)[0] == "falsified"
    assert L.grade_lowweight(_br(pred, weight=80.0), 0.0, L.CONST_DEFAULT, True)[0] == "unmeasured"
    assert L.grade_lowweight(_br(0.0), 0.0, 0.0, False)[0] == "as_predicted"
    assert L.grade_lowweight(_br(0.1), 0.0, 0.0, False)[0] == "falsified"
    assert abs(L.lw_excess(_br(1.0), 0.1) - 0.7) < 1e-9


def test_grade_route():
    assert L.grade_route({"ok": True, "value": "nil"}, {"ok": True, "value": "0.0"}, 0.0)[0] == "as_predicted"
    assert L.grade_route({"ok": True, "value": "nil"}, {"ok": True, "value": "0.0165"}, 0.0)[0] == "falsified"
    assert L.grade_route({"ok": False}, {"ok": True, "value": "0.0"}, 0.0)[0] == "falsified"
    assert L.grade_route({"ok": True}, {"ok": False}, 0.0)[0] == "unmeasured"


def test_grade_persist():
    e = {"const": {"ok": True, "value": "0.016499999910593033"}, "moddata": {"ok": True,
                                                                             "value": {L.MODDATA_KEY: L.MODDATA_VAL}},
         "health": {"overall": 100.0}, "health_k": 70.0, "marker_read": L.CONST_MARKER}
    assert L.grade_persist(e)[0] == "as_predicted"
    assert L.grade_persist(dict(e, const={"ok": True, "value": "0.0042"}))[0] == "falsified"
    assert L.grade_persist(dict(e, moddata={"ok": True, "value": {}}))[0] == "unmeasured"
    assert L.grade_persist(dict(e, moddata={"ok": True, "value": []}, health={"overall": 72.0}))[0] == "as_predicted"


def test_grade_z():
    assert L.grade_z({"logs": {"mod_error": {"a": []}}, "admin_lua_error": False})[0] == "as_predicted"
    assert L.grade_z({"logs": {"mod_error": {"a": ["NR_X.lua failed:"]}}, "admin_lua_error": False})[0] == "falsified"
    assert L.grade_z({"logs": {"mod_error": {"a": []}}, "admin_lua_error": True})[0] == "falsified"
    assert L.grade_z({})[0] == "unmeasured"


def test_counts_of_takes_an_empty_list():
    assert L.counts_of({"counts": []}) == {} and L.counts_of({"counts": {"SICK": 3}}) == {"SICK": 3}


# ---------------------------------------------------------------- the pre-boot checks
def test_harness_markers_are_in_the_repository():
    found, ok = L.harness_markers_ok()
    assert ok, found


def test_deployed_marker_check_on_a_run_layout():
    with tempfile.TemporaryDirectory() as d:
        for fname, rel in L.HARNESS_FILES.items():
            side = rel.split("/")[-2]
            dst = os.path.join(d, "server", "Zomboid", "mods", "PZTestKit", "42", "media", "lua", side, fname)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(REPO, rel), dst)
        dm, ok = X.deployed_marker_check(d, list(L.HARNESS_MARKERS), L.HARNESS_MARKERS)
        assert ok, dm
        p = os.path.join(d, "server", "Zomboid", "mods", "PZTestKit", "42", "media", "lua", "server",
                         "PZTestKit_Server.lua")
        with open(p, "w", encoding="utf-8") as out:
            out.write("-- emptied")
        assert X.deployed_marker_check(d, list(L.HARNESS_MARKERS), L.HARNESS_MARKERS)[1] is False


def test_staged_gate_on_a_real_staged_copy_of_the_pinned_commit():
    import release_pack as RP
    with tempfile.TemporaryDirectory() as d:
        arch = subprocess.run(["git", "archive", "--format=tar", L.STAGED_FROM, L.MOD_DIR], cwd=REPO,
                              capture_output=True, check=True)
        with tarfile.open(fileobj=io.BytesIO(arch.stdout)) as tf:
            tf.extractall(os.path.join(d, "src"), filter="data")
        RP.stage(os.path.join(d, "src", *L.MOD_DIR.split("/")), os.path.join(d, "out"))
        root = os.path.join(d, "out", "NutritionRevamp")
        mod = os.path.join(root, "Contents", "mods", "NutritionRevamp")
        mg = L.staged_gate(stage_root=root, stage_mod=mod)
        assert mg["ok"] and mg["staged_version"] == "1.0.0", mg
        with open(os.path.join(mod, *L.STAGED_CORE.split("/")), "a", encoding="utf-8") as fh:
            fh.write("\n-- drift\n")
        assert L.staged_gate(stage_root=root, stage_mod=mod)["ok"] is False


def test_preboot_passes_on_the_repository():
    spec = L.SESSIONS["S1"]
    if any(d.startswith(spec["prefix"] + "-") for d in os.listdir(os.path.join(REPO, "testing", "artifacts"))):
        pytest.skip("the session has run; its committed artifact is the evidence "
                    "(test_preboot_refuses_a_committed_artifact covers the refusal)")
    drv = "x451_capspike.py"
    checks, ok = L.preboot(spec["profile"], spec["prefix"], drv)
    assert ok, checks
    assert L.preboot(spec["profile"], "x999", drv)[1] is False
    assert L.preboot("x44-mod", spec["prefix"], drv)[1] is False


def test_preboot_refuses_a_committed_artifact(tmp_path):
    shutil.copytree(os.path.join(REPO, "testing", "profiles"), tmp_path / "testing" / "profiles")
    for rel in L.HARNESS_FILES.values():
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(os.path.join(REPO, rel), dst)
    (tmp_path / "testing" / "artifacts").mkdir()
    assert L.preboot("x45-mod", "x451", "x451_capspike.py", repo=str(tmp_path))[1] is True
    (tmp_path / "testing" / "artifacts" / "x451-20261016-100000").mkdir()
    checks, ok = L.preboot("x45-mod", "x451", "x451_capspike.py", repo=str(tmp_path))
    assert ok is False and checks["no_prior_artifact"] is False


def test_profile_doc_checks_fail_a_wrong_profile():
    import tomllib
    with open(os.path.join(REPO, "testing", "profiles", "x45-mod.toml"), encoding="utf-8") as fh:
        text = fh.read()
    doc = tomllib.loads(text)
    assert all(L.profile_doc_checks("x45-mod", doc, text).values())
    bad = dict(doc, sandbox=dict(doc["sandbox"], Nutrition=True))
    assert L.profile_doc_checks("x45-mod", bad, text)["nutrition_false"] is False
    bad = dict(doc, server={"SleepAllowed": True, "SleepNeeded": True})
    assert L.profile_doc_checks("x45-mod", bad, text)["sleep_off"] is False
    assert L.profile_doc_checks("x44-mod", doc, text)["named_profile"] is False


def test_driver_names_its_session():
    src = open(os.path.join(REPO, "testing", "experiments", "x451_capspike.py"), encoding="utf-8").read()
    assert 'PREFIX = "x451"' in src and 'PROFILE = "x45-mod"' in src and "import x45_lib as L" in src
