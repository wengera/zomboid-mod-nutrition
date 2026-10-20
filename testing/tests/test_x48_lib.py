"""Offline tests of testing/experiments/x48_lib.py and x48_prerun.py (Plan 17 Task 4, runs x481 and x482): every grade
with a failing case and its unmeasured case; the write placement; the pre-boot checks on the real repository, the real
staged copy, the real fixture and a real run layout; the prerun current at HEAD; and each session's body run against a
fake world behind a fake bus, once as predicted and once per defect flag that must move a named grade off as_predicted.

The fake world is the mod itself: the real server adapters on the replay host (tools/replay_live.ServerReplay from the
first sight, the session's options, game_heal on), stepped once a game minute as the game clock passes at the session's
speed (DayLength 4: a game hour 225 wall s at speed 1), the minute ring's row read before each minute's drain (the
harness's order). A defect flag patches that world (a kernel constant, an ignored write, a late or absent switch, a
held-back take). The grading replays the real HEAD replay against the fake ring, so the as-predicted run also checks the
write placement and the replay inputs end to end.

The fake bus answers the harness's real reply shapes, read off the handlers' `@reply` lines
(docs/reference/harness-commands.md): ping the string "pong"; time.snapshot {worldAge, hour, minutes, mult, trueMult,
wall}; players a list of names; lua.read {ok, side, root, n, values, tables, types, missing}; lua.global {side, name,
resolved, type, value}; record.set {ok, side, user, path, key, keyType, before, beforeType, after, afterType};
sandbox.var {ok, path, requested, before, after [, reason]}; health.get {ok, side, overall, health, parts};
witness.chain {ok, value, hops} with the end value tostring'd; stats.all {side, user, worldAge, mult, wall, stats,
missing}; nutrition.get {calories, carbs, lipids, proteins, weight, ...}; minute.ring start {ok, side, user, armed, cap,
paths, stats, online, probe}, read {ok, side, user, from, rows, skipped, next, more, ..., errors, result, file}, stop
{ok, side, user, stopped, recorded, overwritten, errors}; time.multiplier the string "mult=<true> eff=<effective>"; RCON
settimespeed as the game's text.
"""
import copy
import json
import math
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x48_lib as L                   # noqa: E402
import x48_prerun as PR               # noqa: E402
import xlib as X                      # noqa: E402
import replay_live as RL              # noqa: E402

REPO = L.REPO
lua51 = None


# ---------------------------------------------------------------- the fake world
class FakeBus:
    def __init__(self, results_dir):
        self.results_dir = results_dir

    def wait_result(self, name, timeout=30, after=None):
        with open(os.path.join(self.results_dir, name + ".json"), encoding="utf-8") as fh:
            return json.load(fh)


class FakeServer:
    def __init__(self, world, results_dir):
        self.w = world
        self.errors = []
        self.bus = FakeBus(results_dir)

    def rcon(self, cmd):
        return self.w.rcon(cmd)


class FakeClient:
    def __init__(self, user):
        self.username = user
        self.seen = {}
        self.alive = True
        self.console = os.devnull


PATCH = {
    "rate_off": "NutritionRevamp.kernel.drain.CAL_DAY_MIN = 95",
    "slope_off": "NutritionRevamp.kernel.drain.A_STARVE = NutritionRevamp.kernel.drain.A_STARVE * 1.2",
    "worst": "NutritionRevamp.kernel.drain.fold = function(acc, f, c) return math.min(acc, f) end",
    "cap_off": ("local D0 = NutritionRevamp.kernel.drain; D0.take = function(D, h) if not D.active then return 0 end "
                "return math.max(0, math.min(h - D.target, 0.9 * D.drainThisMinute)) end"),
    "slow_line": "NutritionRevamp.kernel.drain.R_HUNGER = NutritionRevamp.kernel.drain.R_HUNGER * 0.95",
    "no_death": ("local D0 = NutritionRevamp.kernel.drain; local t0 = D0.take; D0.take = function(D, h) "
                 "return math.max(0, math.min(t0(D, h), h - 0.5)) end"),
}


class World:
    """The mod on the replay host as the game clock passes (see the module docstring). `flags` are defects."""
    GH_S = 225.0                         # a game hour at speed 1, DayLength 4

    def __init__(self, results_dir, key, flags=()):
        global lua51
        self.dir = results_dir
        self.f = set(flags)
        prof = L.PROFILES[L.SESSIONS[key]["profile"]]
        pace = 2 if "opt_wrong" in self.f else prof["pace"]
        self.be = RL.ServerReplay(hour_offset=L.HOUR_OFFSET, rng="half", sleep_allowed=False,
                                  stats=dict(L.FIRST_SIGHT["stats"]), player=dict(L.FIRST_SIGHT["player"]),
                                  death_pace=pace, health_combine=prof["combine"], day_minutes=L.DAY_MIN,
                                  game_heal=True)
        lua51 = self.be.lua51
        for k, src in PATCH.items():
            if k in self.f:
                self.be.rt.execute(src)
        self.t, self.speed = 0.0, 1.0
        self.age = L.FIRST_SIGHT["age"] - 1.0 / 60.0
        self.k = 0
        self.ring, self.ring_on, self.paths, self.s = [], False, [], 0
        self.delayed = []
        self.dead = False
        self.saves = 0
        self.step_minute()                                     # the first sight

    # -- the clock
    def clock(self):
        return self.t

    def sleep(self, dt):
        end = self.t + dt
        while True:
            nxt = (math.floor(self.age * 60.0 + 1e-9) + 1) / 60.0
            dt_wall = (nxt - self.age) * self.GH_S / self.speed
            if self.t + dt_wall > end + 1e-12:
                self.age += (end - self.t) * self.speed / self.GH_S
                self.t = end
                return
            self.t += dt_wall
            self.age = nxt
            self.step_minute()

    def step_minute(self):
        a = self.age
        for item in [d for d in self.delayed if d[0] <= a + 1e-12]:
            self.delayed.remove(item)
            self.set_global(item[1], item[2])
        if self.ring_on:
            self.s += 1
            row = self.be.row(self.paths)
            row.pop("satiety.hModel", None)
            row.update({"s": self.s, "ev": self.s, "age": a, "dtM": 1.0, "drained": self.k,
                        "dead": self.dead})
            if not self.dead:
                row["health"] = self.health()
            self.ring.append(row)
        if not self.dead:
            self.be.step(a)
            self.k += 1
            if self.health() <= 0.0:
                self.dead = True
                self.be.p.deadFlag = True

    def health(self):
        bd = self.be.p.getBodyDamage(self.be.p)
        return float(bd.getOverallBodyHealth(bd))

    # -- reads and writes
    def walk(self, path, root=None):
        segs, glob = RL.parse_path(path)
        return RL.walk(self.be.lua51, self.be.G if glob else self.be.record(), segs)

    def set_record(self, path, value):
        segs, glob = RL.parse_path(path)
        ok, parent = RL.walk(self.be.lua51, self.be.record(), segs[:-1]) if len(segs) > 1 else (True,
                                                                                                 self.be.record())
        if not ok:
            return None
        parent[segs[-1][1]] = value
        return value

    def set_global(self, path, value):
        segs, _ = RL.parse_path("_G." + path)
        ok, parent = RL.walk(self.be.lua51, self.be.G, segs[:-1])
        parent[segs[-1][1]] = value

    def snapshot(self):
        tod = math.fmod(self.age + L.HOUR_OFFSET, 24.0)
        return {"worldAge": self.age, "hour": int(tod), "minutes": int((tod % 1) * 60), "mult": self.speed * 4.75,
                "trueMult": self.speed, "wall": self.t}

    def rcon(self, cmd):
        m = re.match(r"settimespeed (\d+)", cmd)
        if m:
            self.speed = float(m.group(1))
            return True, f"Time speed set to {m.group(1)}"
        return False, "Unknown command"

    def lread(self, root, paths):
        values, missing, types = {}, {}, {}
        for p in paths:
            ok, v = self.walk(("_G." + p) if root == "_G" else p)
            if ok:
                values[p] = RL._scalar(self.be.lua51, v)
                types[p] = type(values[p]).__name__
            else:
                missing[p] = "absent"
        return {"ok": True, "side": "server", "root": root, "n": len(paths), "values": values, "tables": {},
                "types": types, "missing": missing}

    def record_text(self):
        """The store's slot line as NR_Server_Store writes it: {gen, rec = K.store.inputsOnly(record), done} in the
        store's own number format."""
        return str(self.be.rt.eval(
            "function(r) local K = NutritionRevamp.kernel; return K.json.encode({ gen = 1, "
            "rec = K.store.inputsOnly(r), done = true }, NutritionRevamp.server.store.file.fmt) end")(self.be.record()))

    def ring_read(self, frm):
        rows = [r for r in self.ring if frm is None or r["s"] >= int(frm)][:720]
        f = rows[0]["s"] if rows else (int(frm) if frm else 1)
        name = f"minute-ring-admin-{f}"
        with open(os.path.join(self.dir, name + ".json"), "w", encoding="utf-8") as fh:
            json.dump({"rows_list": rows, "paths": self.paths}, fh)
        nxt = (rows[-1]["s"] + 1) if rows else f
        return {"ok": True, "side": "server", "user": "admin", "from": f, "rows": len(rows), "skipped": 0,
                "next": nxt, "more": nxt <= len(self.ring), "oldest": 1, "newest": len(self.ring), "errors": 0,
                "result": name, "file": "pzt-results/" + name + ".json"}

    def ask(self, node, cmd, args="", timeout=30):
        a = args.split() if isinstance(args, str) else list(args)
        if cmd == "ping":
            return "pong"
        if cmd == "time.snapshot":
            return self.snapshot()
        if cmd == "players":
            return ["admin"]
        if cmd == "time.multiplier":
            if a:
                self.speed = float(a[0])
            return f"mult={self.speed} eff={self.speed * 4.75}"
        if cmd == "lua.read":
            root = a[0]
            return self.lread("_G" if root == "_G" else "record", a[1:])
        if cmd == "lua.global":
            if a[0] == "NutritionRevamp.server.store.file.last.admin":
                return {"side": "server", "name": a[0], "resolved": True, "type": "string",
                        "value": self.record_text()}
            ok, v = self.walk("_G." + a[0])
            return {"side": "server", "name": a[0], "resolved": ok, "type": type(v).__name__,
                    "value": RL._scalar(self.be.lua51, v) if ok else None}
        if cmd == "record.set":
            path, raw = a[1], a[2]
            ok, before = self.walk(path)
            value = float(raw)
            ignored = (path == "drain.fedAgeH" and "no_onset" in self.f) or \
                      (path == "nutrients.thiamine.p" and "no_beri" in self.f)
            if not ignored:
                self.set_record(path, value)
            _, after = self.walk(path)
            return {"ok": True, "side": "server", "user": a[0], "path": path, "key": path.split(".")[-1],
                    "keyType": "string", "before": before if ok else None, "beforeType": "number",
                    "after": after, "afterType": "number"}
        if cmd == "sandbox.var":
            path, value = a[0], float(a[1])
            _, before = self.walk("_G.SandboxVars." + path)
            if "late_follow" in self.f:
                self.delayed.append((self.age + 3.0 / 60.0, "SandboxVars." + path, value))
            elif "no_follow" not in self.f:
                self.set_global("SandboxVars." + path, value)
            return {"ok": True, "path": path, "requested": value, "before": before, "after": value}
        if cmd == "health.get":
            h = 0.0 if self.dead else self.health()
            return {"ok": True, "side": "server", "overall": h, "health": h, "parts": []}
        if cmd == "witness.chain":
            if a[1] == "isDead":
                return {"ok": True, "value": "true" if self.dead else "false", "hops": 1}
            return {"ok": True, "value": "0.0165", "hops": 2}
        if cmd == "stats.all":
            sv = self.be.p.sv
            return {"side": "server", "user": "admin", "worldAge": self.age, "mult": self.speed, "wall": self.t,
                    "stats": {"Hunger": sv["HUNGER"], "Thirst": sv["THIRST"], "Fatigue": sv["FATIGUE"],
                              "Boredom": sv["BOREDOM"] or 0.0, "Unhappiness": sv["UNHAPPINESS"] or 0.0},
                    "missing": []}
        if cmd == "nutrition.get":
            n = self.be.p.getNutrition(self.be.p)
            return {"calories": n.cal, "carbs": n.carb, "lipids": n.lip, "proteins": n.pro, "weight": n.weight}
        if cmd == "minute.ring":
            if a[1] == "start":
                self.ring, self.ring_on, self.paths, self.s = [], True, a[2:], 0
                return {"ok": True, "side": "server", "user": "admin", "armed": True, "cap": 4320, "paths": a[2:],
                        "stats": [], "online": True, "probe": None}
            if a[1] == "read":
                return self.ring_read(a[2] if len(a) > 2 else None)
            self.ring_on = False
            return {"ok": True, "side": "server", "user": "admin", "stopped": True, "recorded": len(self.ring),
                    "overwritten": 0, "errors": 0}
        return {"error": f"the fake has no {cmd}"}

    def flush_paths(self):
        pass


def fake_lread_saves(w):
    """W's store save: the lastWrite counter rises every 10 wall seconds."""
    orig = w.lread

    def lread(root, paths):
        out = orig(root, [p for p in paths if "store.file.lastWrite" not in p and "players.online" not in p])
        for p in paths:
            if "store.file.lastWrite" in p:
                out["values"][p] = math.floor(w.t / 10.0) * 10000.0
            elif "players.online" in p:
                out["values"][p] = True
        return out
    w.lread = lread


def fresh_out():
    return {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
            "world_changes": {"left_in_place": []}}


def run_session(key, tmp_path, flags=(), budget=1e9):
    d = str(tmp_path)
    os.makedirs(d, exist_ok=True)
    w = World(d, key, flags)
    fake_lread_saves(w)
    out = fresh_out()
    xs = X.Xs(out, node=lambda side: side, clients={"admin": FakeClient("admin")}, ask=w.ask, budget_s=budget,
              clock=w.clock, sleep=w.sleep, spawn_wait_s=0.5)
    xs.server = FakeServer(w, d)
    S = L.Sess(xs, key, run_dir=d)
    for _ in range(int(0.25 * 60)):                            # S/H take game time before the seed, as live
        w.sleep(w.GH_S / 60.0)
    S.body_run(S.phases())
    out["logs"] = {"mod_error": []}
    out["admin_lua_error"] = False
    S.grade_all()
    v = {k: x["verdict"] for k, x in out["verdicts"].items()}
    return v, out, w, S


def bad(v, out):
    return {k: (x, out["verdicts"][k]["observed"]) for k, x in v.items() if x != "as_predicted"}


NAMES = {
    "x481": {"OPT", "ONSET", "OPEN_RATE", "OPEN_SLOPE", "BERI_ON", "COMBINE", "FOLLOW", "CAP", "REPLAY_health",
             "REPLAY_drain.target", "H1", "RING", "Z"},
    "x482": {"OPT", "ONSET", "SLOPE", "DEATH", "REPLAY_health", "REPLAY_drain.target", "H1", "RING", "Z"},
}


@pytest.fixture(scope="module")
def as_predicted(tmp_path_factory):
    return {k: run_session(k, tmp_path_factory.mktemp(k)) for k in NAMES}


@pytest.mark.parametrize("key", sorted(NAMES))
def test_session_as_predicted(key, as_predicted):
    v, out, w, S = as_predicted[key]
    assert set(v) == NAMES[key]
    assert not bad(v, out), bad(v, out)
    assert not out["phase_errors"] and not out.get("skipped_phases")
    assert out["replay"]["fields"]["health"]["n"] > 50 and out["replay"]["fields"]["drain.target"]["n"] > 50


def test_x481_places_its_writes_and_restores_the_pace(as_predicted):
    v, out, w, S = as_predicted["x481"]
    book = {b["path"]: b for b in out["model_inputs"]["placement"]}
    rows = S.ring_rows()
    for st in S.sets:                          # the fake's minute reads and drains at once: every set shows first
        b = book[st["path"]]
        assert b["how"] == "shown" and b["s"] == next(r["s"] for r in rows if r["age"] > st["age"]), b
    assert book["_G.SandboxVars.NR.DeathPace"]["how"] == "shown"
    assert out["checks"]["SW"]["write"]["read_before"] == 3
    assert out["checks"]["K"]["restore"]["ok"] is True
    assert w.walk("_G.SandboxVars.NR.DeathPace")[1] == 3
    fol = out["verdicts"]["FOLLOW"]["observed"]
    assert fol["lag_gm"] <= L.FOLLOW_GM and abs(fol["arm_on"] - fol["arm_off"]) > L.DISCRIM
    op = out["verdicts"]["OPEN_SLOPE"]["observed"]
    assert op["body_ratio"] < 0.7 and op["rel"] < 1e-6                 # the 80 kg body opens at 0.665 of r_hunger(90)
    assert [r["trueMult"] for r in S.speeds][-1] == 1.0                 # the clock restored to the start's


def test_x482_dies_on_the_line_and_reads_x442(as_predicted):
    v, out, w, S = as_predicted["x482"]
    dv = out["verdicts"]["DEATH"]["observed"]
    assert dv["source"] == "ring" and abs(dv["miss_h"]) <= L.DEATH_TOL_H
    rd = out["checks"]["x442"]
    assert rd["after_onset_h"] == pytest.approx(100.0 / L.r_hunger(90), abs=0.05)
    assert rd["diff_after_write_h"] == pytest.approx(rd["after_seed_h"] - 36.446332, abs=1e-5)
    assert "server-stdout.log" not in S.xs.copied                       # copied only by main's log read, if present


FLAGS = [
    ("x481", "opt_wrong", {"OPT"}),
    ("x481", "no_onset", {"ONSET"}),
    ("x481", "rate_off", {"OPEN_RATE"}),
    ("x481", "slope_off", {"OPEN_SLOPE"}),
    ("x481", "no_beri", {"BERI_ON", "COMBINE"}),
    ("x481", "worst", {"COMBINE", "REPLAY_drain.target"}),
    ("x481", "late_follow", {"FOLLOW"}),
    ("x481", "no_follow", {"FOLLOW"}),
    ("x481", "cap_off", {"CAP", "REPLAY_health"}),
    ("x482", "opt_wrong", {"OPT"}),
    ("x482", "slow_line", {"SLOPE", "DEATH"}),
    ("x482", "no_death", {"DEATH"}),
]


@pytest.mark.parametrize("key,flag,grades", FLAGS)
def test_each_defect_moves_its_grade(key, flag, grades, tmp_path):
    v, out, w, S = run_session(key, tmp_path, flags=(flag,))
    moved = {k for k, x in v.items() if x != "as_predicted"}
    assert grades <= moved, (flag, bad(v, out))


def test_the_budget_stops_the_scenario_and_keeps_the_closing_phases(tmp_path):
    v, out, w, S = run_session("x482", tmp_path, budget=120.0)
    assert out["budget_stop"] and "D" in out["phase_walls"]
    assert {"E", "C", "R"} <= set(out["phase_walls"])
    assert v["DEATH"] == "unmeasured" and out["checks"]["projection"]["projected_age"] > 0


# ---------------------------------------------------------------- the pure grades
def _rows(n, a0=3.0, **fields):
    rows = []
    for i in range(n):
        r = {"s": i + 1, "age": a0 + i / 60.0, "on": True}
        for k, f in fields.items():
            r[k] = f(i) if callable(f) else f
        rows.append(r)
    return rows


def test_place_set_by_before_by_shown_and_by_age():
    rows = _rows(6, M=lambda i: 100.0 - 10 * i)
    a = rows[2]["age"]
    assert L.place_set(rows, "M", 0.0, 80.0, a, a + 0.001) == (3, "before")          # read, then the set: drain 3
    rows2 = copy.deepcopy(rows)
    rows2[3]["M"] = 0.0                                                               # the set before row 4's read
    assert L.place_set(rows2, "M", 0.0, 70.0, rows[3]["age"] - 0.005, rows[3]["age"] - 0.004) == (4, "shown")
    assert L.place_set(rows, "M", 5.0, 33.0, a, a + 0.001) == (4, "age")
    flat = _rows(6, p=lambda i: 1.0 if i < 3 else 0.3 - 0.001 * (i - 3))      # p at its cap until the set
    b = flat[2]["age"] + 0.002
    assert L.place_set(flat, "p", 0.3, 1.0, b, b) == (4, "shown")                  # never the capped row before it
    flat[3]["p"] = 0.2999                                                           # the set came before drain 3
    assert L.place_set(flat, "p", 0.3, 1.0, flat[2]["age"] + 0.0001, flat[2]["age"] + 0.0002) == (3, "before")
    assert L.place_set(rows, "M", 5.0, 33.0, 99.0, 99.0) == (None, "unplaced")


def test_place_sandbox_is_the_first_row_reading_the_new_value():
    rows = _rows(6, P=lambda i: 3 if i < 4 else 2)
    assert L.place_sandbox(rows, "P", 2, rows[2]["age"]) == (5, "shown")
    assert L.place_sandbox(rows, "P", 1, rows[2]["age"]) == (None, "unplaced")
    ev, book = L.build_events(rows, [], [{"ok": True, "path": "_G.SandboxVars.NR.DeathPace", "ring_path": "P",
                                          "value": 2, "age_before": rows[2]["age"], "tag": "x"},
                                         {"ok": False, "path": "_G.SandboxVars.NR.DeathPace"}])
    assert ev == [{"s": 5, "kind": "setpath", "path": "_G.SandboxVars.NR.DeathPace", "value": 2, "label": "x"}]
    assert book[1]["skipped"]


def test_build_events_skips_a_failed_set_and_uses_the_read_back():
    rows = _rows(4, M=lambda i: 50.0 - i)
    sets = [{"tag": "a", "path": "M", "value": "0", "age": rows[1]["age"], "age_before": rows[1]["age"],
             "reply": {"ok": True, "before": 49.0, "after": 0.0}},
            {"tag": "b", "path": "M", "value": "1", "age": 9.0, "reply": {"ok": False}}]
    ev, book = L.build_events(rows, sets)
    assert ev == [{"s": 2, "kind": "setpath", "path": "M", "value": 0.0, "label": "a"}] and book[1]["skipped"]


def test_grade_h1_allows_only_the_onset_paths_missing():
    st = {"ok": True}
    assert L.grade_h1({"missing": {"drain.frac.1": "absent", "drain.pAt": "absent"}}, st)[0] == "as_predicted"
    assert L.grade_h1({"missing": {"drain.target": "absent"}}, st)[0] == "falsified"
    assert L.grade_h1({"missing": {}}, {"ok": False})[0] == "falsified"


def _opt_row(pace, combine, day=90.0, **over):
    r = {"s": 1, L.SB_PACE: pace, L.SB_COMBINE: combine, L.POLLED_PACE: pace, L.POLLED_COMBINE: combine,
         L.OPT_PACE: pace, L.OPT_COMBINE: combine, L.OPT_DAYMIN: day}
    r.update(over)
    return r


def test_grade_opt():
    assert L.grade_opt([_opt_row(3, 2)], 3, 2)[0] == "as_predicted"
    assert L.grade_opt([_opt_row(3, 2, **{L.OPT_PACE: 2})], 3, 2)[0] == "falsified"
    assert L.grade_opt([_opt_row(3, 2, day=15.0)], 3, 2)[0] == "falsified"
    assert L.grade_opt([], 3, 2)[0] == "unmeasured"


def _starve_rows(n=40, on_at=5, **kw):
    return _rows(n, **{"drain.starveAcute": lambda i: i >= on_at, "drain.active": lambda i: i >= on_at}, **kw)


def test_grade_onset():
    rows = _starve_rows()
    assert L.grade_onset(rows, rows[0]["age"])[0] == "as_predicted"
    late = _starve_rows(n=60, on_at=40)
    assert L.grade_onset(late, late[0]["age"])[0] == "falsified"
    never = _starve_rows(n=40, on_at=99)
    assert L.grade_onset(never, never[0]["age"])[0] == "falsified"
    short = _starve_rows(n=3, on_at=99)
    assert L.grade_onset(short, short[0]["age"])[0] == "unmeasured"
    assert L.grade_onset([], 1.0)[0] == "unmeasured"


def test_grade_open_rate():
    rows = _starve_rows(**{"drain.rate": 85.536, L.OPT_DAYMIN: 90.0})
    assert L.grade_open_rate(rows, 5)[0] == "as_predicted"
    rows[10]["drain.rate"] = 85.536 * 1.02
    assert L.grade_open_rate(rows, 5)[0] == "falsified"
    assert L.grade_open_rate(rows, 5, 10)[0] == "as_predicted"         # the row past the end is not read
    assert L.grade_open_rate(rows, None)[0] == "unmeasured"


def _curve_rows(bmi0=27.66868, scale=1.0, n=12, on=3):
    dbmi = L.K_STARVE_DPDT * (L.K_CAL_BMI0 - L.K_BMI_DEATH)
    rows = _starve_rows(n=n, on_at=on, **{"drain.bmi0": bmi0, "drain.rate": 85.536})
    a_on = rows[on - 1]["age"]
    for i, r in enumerate(rows):
        p = dbmi * (rows[i - 1]["age"] - a_on) / (bmi0 - L.K_BMI_DEATH) if i >= on else 0.0
        r["health"] = 100.0 - scale * 100.0 * (1.0 - L.curve(p, 1.0, L.K_A_STARVE))
    return rows


def test_open_pred_and_grade_open_slope():
    rows = _curve_rows()
    op = L.open_pred(rows, 3)
    assert op["live"] == pytest.approx(op["pred"], rel=1e-9) and op["body_ratio"] == pytest.approx(0.6652, abs=1e-3)
    assert op["slope0"] == pytest.approx(L.r_hunger(90) * op["body_ratio"], rel=1e-9)
    assert L.grade_open_slope(op)[0] == "as_predicted"
    assert L.grade_open_slope(L.open_pred(_curve_rows(scale=1.05), 3))[0] == "falsified"
    light = _curve_rows(bmi0=19.0)                                     # a lighter body: the cap binds
    opl = L.open_pred(light, 3)
    assert opl["pred"] <= 85.536 / 24.0 + 1e-9
    assert L.open_pred(rows, None) is None and L.grade_open_slope(None)[0] == "unmeasured"


def test_grade_beri():
    rows = _rows(20, **{"nutrients.thiamine.g": lambda i: 4 if i >= 6 else 1,
                        L.F3: lambda i: (1.0 - (i - 6) / 50400.0) if i >= 6 else None})
    a = rows[4]["age"] + 0.001
    assert L.grade_beri(rows, a)[0] == "as_predicted"
    assert L.grade_beri(rows, rows[1]["age"])[0] == "falsified"         # five minutes late
    none = _rows(20, **{"nutrients.thiamine.g": 1})
    assert L.grade_beri(none, a)[0] == "falsified"
    assert L.grade_beri(none[:5], none[4]["age"])[0] == "unmeasured"
    assert L.grade_beri(rows, None)[0] == "unmeasured"


def test_grade_combine():
    rows = _rows(5, **{L.F1: 0.9, L.F3: 0.99, "drain.target": 100.0 * 0.9 * 0.99, L.OPT_COMBINE: 2})
    assert L.grade_combine(rows)[0] == "as_predicted"
    rows[2]["drain.target"] = 90.0                                     # Worst only
    assert L.grade_combine(rows)[0] == "falsified"
    rows = _rows(5, **{L.F1: 0.9, L.F3: 0.99, "drain.target": 89.1, L.OPT_COMBINE: 1})
    assert L.grade_combine(rows)[0] == "falsified"
    assert L.grade_combine(_rows(5, **{L.F1: 0.9}))[0] == "unmeasured"


def _arms(rows, k_sw, jump=1.7):
    on = [{"s": r["s"], "drain.target": r["drain.target"] - (jump if r["s"] > k_sw else 0.0)} for r in rows]
    off = [{"s": r["s"], "drain.target": r["drain.target"]} for r in rows]
    return on, off


def test_grade_follow():
    rows = _rows(30, **{"drain.target": lambda i: 97.0 - 0.05 * i})
    on, off = _arms(rows, 11)
    live = copy.deepcopy(rows)
    for r in live:
        if r["s"] > 11:
            r["drain.target"] -= 1.7
    a = rows[10]["age"] - 0.002                                        # the write before drain 11 (ring row s 11)
    assert L.grade_follow(live, on, off, a)[0] == "as_predicted"
    late = copy.deepcopy(rows)
    for r in late:
        if r["s"] > 14:
            r["drain.target"] -= 1.7
    assert L.grade_follow(late, on, off, a)[0] == "falsified"
    assert L.grade_follow(rows, on, off, a)[0] == "falsified"          # never followed
    assert L.grade_follow(rows, off, off, a)[0] == "unmeasured"        # the arms never part
    assert L.grade_follow(rows, on, off, None)[0] == "unmeasured"


def test_grade_cap():
    rate = 88.393
    rows = _rows(20, **{"drain.rate": rate, "drain.target": 90.0,
                        "health": lambda i: 95.0 - rate / 1440.0 * i})
    assert L.grade_cap(rows, rows[0]["age"] - 0.01)[0] == "as_predicted"
    slow = _rows(20, **{"drain.rate": rate, "drain.target": 90.0, "health": lambda i: 95.0 - 0.95 * rate / 1440.0 * i})
    assert L.grade_cap(slow, slow[0]["age"] - 0.01)[0] == "falsified"
    near = _rows(20, **{"drain.rate": rate, "drain.target": 90.0, "health": 90.1})
    assert L.grade_cap(near, near[0]["age"] - 0.01)[0] == "unmeasured"


def test_grade_slope():
    r = L.r_hunger(90)
    rows = _rows(200, **{"drain.active": True, L.OPT_DAYMIN: 90.0, "health": lambda i: 99.0 - r / 60.0 * i})
    assert L.grade_slope(rows)[0] == "as_predicted"
    slow = _rows(200, **{"drain.active": True, L.OPT_DAYMIN: 90.0, "health": lambda i: 99.0 - 0.97 * r / 60.0 * i})
    assert L.grade_slope(slow)[0] == "falsified"
    assert L.grade_slope(_rows(2, **{"drain.active": False, "health": 50.0}))[0] == "unmeasured"


def test_death_live_replay_and_grade_death():
    rows = _rows(10, health=lambda i: max(0.0, 5.0 - i), dead=lambda i: i >= 7)
    assert L.death_live(rows) == (rows[5]["age"], "ring")              # health 0 before the dead flag
    alive = _rows(10, health=50.0, dead=False)
    assert L.death_live(alive, [{"dead": False, "age": 1.0}, {"dead": True, "age": 3.2}]) == (3.2, "poll")
    assert L.death_live(alive) == (None, None)
    assert L.death_replay([{"age": 1.0, "health": 3.0}, {"age": 1.1, "health": 0.0}]) == 1.1
    assert L.grade_death(10.02, 10.0)[0] == "as_predicted"
    assert L.grade_death(10.2, 10.0)[0] == "falsified"
    assert L.grade_death(None, 10.0, last_age=10.3)[0] == "falsified"
    assert L.grade_death(None, 10.0, last_age=9.0)[0] == "unmeasured"
    assert L.grade_death(10.0, None)[0] == "unmeasured"


def test_projection_and_the_x442_reading():
    rows = _rows(100, **{"drain.active": True, "health": lambda i: 60.0 - 0.0594 * i})
    p = L.projection(rows)
    assert p["projected_age"] == pytest.approx(rows[0]["age"] + 60.0 / (0.0594 * 60.0), rel=1e-6)
    assert L.projection(rows[:1]) is None
    rd = L.x442_reading(30.0, 2.0, 2.1)
    assert rd["after_seed_h"] == 28.0 and rd["diff_after_onset_h"] == pytest.approx(27.9 - 28.121130, abs=1e-5)
    assert L.x442_reading(None, 1, 1)["why"]
    assert len(L.rows_upto_death(_rows(10, health=lambda i: 5.0 - i))) == 6


def test_the_x442_constants_are_the_artifacts():
    p = os.path.join(REPO, "testing", "artifacts", "x442-20261015-173502", "starve.json")
    with open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    assert d["checks"]["X"]["write"]["ages"][1] == L.X442_WRITE_AGE
    assert d["checks"]["X"]["death"]["age"] == L.X442_DEATH_AGE
    with open(os.path.join(REPO, "docs", "reference", "claims.tsv"), encoding="utf-8") as fh:
        row = next(ln for ln in fh if ln.startswith("#3882\t"))
    assert repr(L.X442_LEVEL4_AGE) in row
    st = d["checks"]["start"]["stats"]
    assert L.FIRST_SIGHT["stats"]["HUNGER"] == st["hunger"] and L.FIRST_SIGHT["player"]["weight"] == st["weight"]


def test_the_kernel_constants_are_the_kernels():
    with open(os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Kernel_Drain.lua"),
              encoding="utf-8") as fh:
        src = fh.read()

    def k(name):
        return float(re.search(r"^K\.drain\." + name + r" = ([0-9.e-]+)", src, re.M).group(1))
    assert k("R_HUNGER") == L.K_R_HUNGER and k("A_STARVE") == L.K_A_STARVE
    assert k("STARVE_DPDT") == L.K_STARVE_DPDT and k("CAL_BMI0") == L.K_CAL_BMI0
    assert k("CAL_DAY_MIN") == L.K_CAL_DAY_MIN and k("BMI_DEATH") == L.K_BMI_DEATH
    assert k("BERIBERI_DEATH_H") == L.K_BERIBERI_DEATH_H and k("CLINICAL") == L.K_CLINICAL
    assert k("STARVE_ONSET_H") == L.STARVE_ONSET_H
    with open(os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Data_Records.lua"),
              encoding="utf-8") as fh:
        rec = fh.read()
    assert re.search(r"0\.4166666666666667, -- clinical = 0\.5/1\.2", rec) and L.THIAMINE_CLINICAL_P == 0.5 / 1.2
    assert L.THIAMINE_P < L.THIAMINE_CLINICAL_P


# ---------------------------------------------------------------- the pre-boot checks
@pytest.mark.parametrize("key", sorted(L.SESSIONS))
def test_preboot_on_the_repository(key):
    s = L.SESSIONS[key]
    pre, ok = L.preboot(key, s["profile"], key, s["driver"])
    if not pre["no_prior_artifact"]:
        pytest.skip("the session's artifact is committed: preboot refuses it by design")
    assert ok, {k: v for k, v in pre.items() if v is not True}


def test_preboot_refuses_a_wrong_prefix_profile_file_artifact_or_stale_prerun(tmp_path):
    s = L.SESSIONS["x481"]
    assert L.preboot("x481", s["profile"], "x482", s["driver"])[1] is False
    assert L.preboot("x481", "x48-vanilla", "x481", s["driver"])[1] is False
    assert L.preboot("x481", s["profile"], "x481", "x482_vanilla.py")[1] is False
    stale = L.preboot("x481", s["profile"], "x481", s["driver"], compute=lambda keys: {"x481": {"x": 1}})
    assert stale[1] is False and stale[0]["prerun_current"] is False
    fake = tmp_path / "repo"
    (fake / "testing" / "artifacts" / "x481-20261020-000000").mkdir(parents=True)
    pre, ok = L.preboot("x481", s["profile"], "x481", s["driver"], repo=str(fake), compute=lambda keys: {})
    assert ok is False and pre["no_prior_artifact"] is False


def test_profile_checks_fail_each_key():
    import tomllib
    for name in L.PROFILES:
        path = os.path.join(REPO, "testing", "profiles", name + ".toml")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        doc = tomllib.loads(text)
        c = L.profile_doc_checks(name, doc, text)
        assert all(c.values()), (name, c)
        muts = {"fixture_default": ("fixture", "two"), "one_admin_client": ("clients", ["admin", "bob"])}
        for key, (k, v) in muts.items():
            d2 = copy.deepcopy(doc)
            d2[k] = v
            assert L.profile_doc_checks(name, d2, text)[key] is False
        for key, sub, k, v in (("sleep_off", "server", "SleepAllowed", True), ("nutrition_false", "sandbox",
                                                                                 "Nutrition", True),
                               ("day_length", "sandbox", "DayLength", 1)):
            d2 = copy.deepcopy(doc)
            d2[sub][k] = v
            assert L.profile_doc_checks(name, d2, text)[key] is False
        d2 = copy.deepcopy(doc)
        d2["sandbox"]["NR"]["DeathPace"] = 2
        assert L.profile_doc_checks(name, d2, text)["nr_block"] is False
        d2 = copy.deepcopy(doc)
        d2["mods"][1]["path"] = "mod/NutritionRevamp"
        assert L.profile_doc_checks(name, d2, text)["mods_staged"] is False
        assert L.profile_doc_checks(name, doc, "# other")["header_names_file"] is False
    assert L.profile_doc_checks("x46-mod", {}, "") == {"known_profile": False}


def test_the_drivers_name_their_own_file_profile_and_artifact():
    import importlib
    for key, s in L.SESSIONS.items():
        m = importlib.import_module(s["driver"][:-3])
        assert m.KEY == key and m.PREFIX == key and m.PROFILE == s["profile"] and m.ARTIFACT == s["artifact"]
        assert set(m.PRED) == NAMES[key]
        assert m.BUDGET_S <= 560.0


def test_the_staged_copy_gate_and_the_harness_markers():
    found, ok = L.harness_markers_ok()
    assert ok, {f: [k for k, v in d.items() if not v] for f, d in found.items()}
    mg = L.staged_gate()
    if mg.get("error") and "MANIFEST" in mg["error"]:
        pytest.skip("release/plan17-x48 is not staged on this machine")
    assert mg["ok"] and mg["staged_version"] == "1.0.0" and mg["commit"] == L.STAGED_FROM


def test_deployed_marker_check_on_a_real_run_layout(tmp_path):
    runs = sorted(glob_runs())
    for fname, rel in L.HARNESS_FILES.items():
        dst = tmp_path / "server" / "mods" / "PZTestKit" / "42" / "media" / "lua" / os.path.basename(
            os.path.dirname(rel)) / fname
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(open(os.path.join(REPO, rel), encoding="utf-8", errors="replace").read(), encoding="utf-8")
    dm, ok = X.deployed_marker_check(str(tmp_path), list(L.HARNESS_MARKERS), L.HARNESS_MARKERS)
    assert ok, dm
    p = next(tmp_path.rglob("PZTestKit_Server.lua"))
    p.write_text(p.read_text(encoding="utf-8").replace("function TK.TMH.sampleHealth", "function TK.TMH.x"),
                 encoding="utf-8")
    assert X.deployed_marker_check(str(tmp_path), list(L.HARNESS_MARKERS), L.HARNESS_MARKERS)[1] is False
    if runs:                                                   # a real run deployed before the health wrap lacks it
        dm2, ok2 = X.deployed_marker_check(runs[-1], list(L.HARNESS_MARKERS), L.HARNESS_MARKERS)
        assert dm2 and ok2 is False


def glob_runs():
    import glob
    return [d for d in glob.glob(os.path.join(REPO, "testing", "runs", "x46*")) if os.path.isdir(d)]


def test_the_fixture_is_fresh():
    fr = L.fixture_fresh()
    if fr.get("error") and "no row" not in fr["error"] and not os.path.isfile(os.path.join(REPO, L.FIXTURE_PLAYERS_DB)):
        pytest.skip("the fixture cache is not provisioned on this machine")
    assert fr["fresh"], fr


# ---------------------------------------------------------------- the prerun
def test_the_committed_prerun_is_the_head_replay():
    have = L.load_prerun()
    now = PR.canonical(PR.compute())
    for k in L.SESSIONS:
        assert have.get(k) == now[k], k
    assert have["_provenance"]["first_sight"] == L.FIRST_SIGHT


def test_the_prerun_predicts_the_grades_as_predicted():
    p = L.load_prerun()
    a, b = p["x481"], p["x482"]
    assert a["open_rate"]["worst_rel"] == 0.0 and a["open"]["live"] == pytest.approx(a["open"]["pred"], rel=1e-6)
    assert a["beri"]["lag_gm"] <= L.BERI_GM and a["follow"]["lag_gm"] <= L.FOLLOW_GM
    assert abs(a["follow"]["arm_on"] - a["follow"]["arm_off"]) > 10 * L.DISCRIM
    assert a["cap"]["slope_h"] == pytest.approx(a["cap"]["want_h"], rel=1e-6) and a["cap"]["n"] >= L.CAP_MIN_ROWS
    assert a["combine_rows"] > 50 and a["end"]["frac3"] < 1.0
    assert b["death_after_onset_h"] == pytest.approx(100.0 / L.r_hunger(90), abs=0.05)
    assert b["slope"]["rel"] < 1e-9


def test_the_prerun_command_checks_and_names_staleness(tmp_path, monkeypatch, capsys):
    assert PR.main(["--check"]) == 0
    monkeypatch.setattr(L, "PRERUN_FILE", "nowhere/x48_prerun.json")
    monkeypatch.setattr(L, "REPO", str(tmp_path))
    assert PR.main(["--check", "x481"]) == 1
    assert "stale: x481" in capsys.readouterr().out


# ---------------------------------------------------------------- the real replay on a ring the replay host wrote
def test_a_ring_read_off_the_replay_host_replays_within_the_tolerance_and_a_misplaced_switch_does_not(tmp_path):
    """The grading path end to end on the real replay: a session world whose sandbox write the placement reads one row
    late fails REPLAY and FOLLOW, so the placement is load-bearing."""
    v, out, w, S = run_session("x481", tmp_path)
    rows = S.ring_rows()
    events, book = L.build_events(rows, S.sets, S.sandbox)
    late = [dict(e, s=e["s"] + 2) if e["path"].startswith("_G.SandboxVars") else e for e in events]
    start, player, st = S.replay_inputs()
    rep, _ = L.replay(rows, late, start, 3, 2, L.DAY_MIN, player, st)
    d = L.replay_diff(rep, rows)
    assert d["fields"]["health"]["over"] > 0 or d["fields"]["drain.target"]["over"] > 0
