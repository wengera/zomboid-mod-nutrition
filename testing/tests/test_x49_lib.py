"""x49_lib (Plan 18 Task 1, the live probe of the symptom levers), offline: every grade's passing and failing case, the
pre-boot checks, the drivers' argument refusal, and each session's phases run end to end against a fake world that
answers the harness's own reply shapes (lua.call {ok, side, path, nargs, r1, r2, r3}; lua.read {ok, side, root, n,
values, tables, types, missing}; bodypart.get {ok, side, parts}; time.snapshot {worldAge, hour, minutes, mult, trueMult,
wall}; players a list of names) and runs vanilla's laws as the jar reads them (PAIN rising 1/500 of its gap a tick and
set at once when lower, added pain falling 0.005 x the multiplier a tick, standing endurance regeneration, ten server
ticks a wall second, 2 x dayMin multiplier units a game minute). A faithful world grades as_predicted; each mutation of
a law the grades stand on falsifies its grade."""
import os
import re
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXP = os.path.join(REPO, "testing", "experiments")
sys.path.insert(0, EXP)
import x49_lib as L                                                           # noqa: E402
import xlib as X                                                              # noqa: E402


# ================================================================ the fake world
class FakeClient:
    def __init__(self, w):
        self.w = w
        self.seen = {}
        self.username = "admin"
        self.alive = True
        self.console = os.devnull

    def quit(self):
        self.w.disconnect()
        self.alive = False
        return 0

    def kill(self):
        self.alive = False


class FakeBus:
    def __init__(self, w):
        self.w = w

    def wait_result(self, name, timeout=30, after=0.0):
        doc = self.w.results.get(name)
        if doc is None:
            raise TimeoutError(name)
        return doc


class FakeServer:
    def __init__(self, w):
        self.w = w
        self.bus = FakeBus(w)
        self.errors = []
        self.alive = True

    def rcon(self, cmd):
        m = re.match(r"settimespeed (\d+)", cmd)
        if m:
            self.w.speed = int(m.group(1))
            return True, "ok"
        return False, "unknown"


class World:
    """Vanilla's laws at the jar's constants, plus the probe's bookkeeping, on a fake clock."""

    def __init__(self, day_min, decay=L.DECAY_PER_UNIT, rise_div=L.RISE_DIV, regen=L.END_REGEN_BASE, saved=True,
                 client_level_shift=0, tick_hz=10.0):
        self.day_min, self.decay, self.rise_div, self.regen = day_min, decay, rise_div, regen
        self.saved, self.shift, self.tick_hz = saved, client_level_shift, tick_hz
        self.t = 1.8e9
        self.speed = 1
        self.gm = 0.0
        self.gm_acc = 0.0
        self.online = True
        self.st = {"pain": 0.0, "part": 0.0, "endurance": 1.0, "stress": 0.0, "nicotine": 0.0, "unhappy": 0.0,
                   "boredom": 0.0, "fatigue": 0.1}
        self.save_part = 0.0
        self.base_pain = {}
        self.results = {}
        self.client_hist = []
        self.lua_reset()

    # -- the probe's Lua state (lost at a restart)
    def lua_reset(self):
        self.holds, self.user, self.track_part = {}, None, 7
        self.mlog, self.ring, self.ring_on = [], [], False
        self.acc = {"ticks": 0, "mult": 0.0}
        self.ticks = 0
        self.snap_s = {}
        self.trk = {"n": 0}
        self.ctrk = {"n": 0}
        self.snap_c = {}

    # -- the clock
    def clock(self):
        return self.t

    def mult(self):
        return 4.8 * self.speed * 10.0 / self.tick_hz

    def sleep(self, dt):
        end = self.t + max(0.0, dt)
        step = 1.0 / self.tick_hz
        while self.t + step <= end + 1e-9:
            self.t += step
            self.tick()
        self.t = end

    def age(self):
        return 100.0 + self.gm / 60.0

    # -- the levels
    @staticmethod
    def levels(st):
        return {"lvPain": L.level_of("pain", st["pain"]), "lvEnd": L.level_of("endurance", st["endurance"]),
                "lvStress": L.level_of("stress", st["stress"] + st["nicotine"]),
                "lvUnhappy": L.level_of("unhappy", st["unhappy"])}

    @staticmethod
    def track(trk, lv):
        for k, v in lv.items():
            if trk.get(k + "Min") is None or v < trk[k + "Min"]:
                trk[k + "Min"] = v
            if trk.get(k + "Max") is None or v > trk[k + "Max"]:
                trk[k + "Max"] = v
        trk["n"] = trk.get("n", 0) + 1

    # -- one server tick: BodyDamage.Update, the player's endurance, the probe's OnTick, then the minute event
    def tick(self):
        m = self.mult()
        if self.online:
            st = self.st
            tgt = L.PAIN_MOD[7] * st["part"]
            st["pain"] = st["pain"] + (tgt - st["pain"]) / self.rise_div if tgt > st["pain"] else tgt
            st["part"] = max(0.0, st["part"] - self.decay * m)
            st["endurance"] = min(1.0, st["endurance"] + self.regen * m * (1 - 0.85 * st["fatigue"]))
            st["stress"] = max(0.0, st["stress"] - 1e-5 * m)
        self.ticks += 1
        self.acc["ticks"] += 1
        self.acc["mult"] += m
        if self.user is not None:
            if not self.online:
                self.snap_s = {"online": False, "n": self.ticks, "ms": self.t * 1000}
            else:
                lv = self.levels(self.st)
                s = dict(self.st, online=True, n=self.ticks, ms=self.t * 1000, age=self.age(), mult=m,
                         trackPart=self.track_part, **lv)
                self.snap_s = s
                self.track(self.trk, lv)
                if self.ring_on:
                    self.ring.append({k: s[k] for k in ("n", "ms", "mult", "pain", "part", "endurance", "stress",
                                                        "unhappy", "lvPain", "lvEnd", "lvStress", "lvUnhappy")})
        if self.online:
            self.client_hist.append(dict(self.st))
            cst = self.client_hist[-2] if len(self.client_hist) > 1 else self.st
            clv = {k: v + self.shift for k, v in self.levels(cst).items()}
            self.snap_c = dict(cst, n=self.ticks, ms=self.t * 1000, cpart=7, **clv)
            self.track(self.ctrk, clv)
        self.gm += m / (2.0 * self.day_min)
        self.gm_acc += m / (2.0 * self.day_min)
        if self.gm_acc >= 1.0:
            self.gm_acc -= 1.0
            self.on_minute()

    def apply(self, h):
        st = self.st
        if h["kind"] == "pain":
            before = st["part"]
            st["part"] = h["value"]
            return before, st["part"], True
        name = {"endcap": "endurance", "stress": "stress", "unhappy": "unhappy", "boredcap": "boredom"}[h["kind"]]
        before = st[name]
        ceiling = h["kind"] in ("endcap", "boredcap")
        if (before > h["value"]) if ceiling else (before < h["value"]):
            st[name] = h["value"]
            return before, st[name], True
        return before, before, False

    def log(self, ev, key, h, before, after, wrote):
        self.mlog.append({"ev": ev, "key": key, "kind": h["kind"], "part": h.get("part"), "value": h["value"],
                          "before": before, "after": after, "wrote": wrote, "age": self.age(), "ms": self.t * 1000,
                          "ticks": self.acc["ticks"], "mult": self.acc["mult"], "tick": self.ticks})

    def on_minute(self):
        if self.online and self.user is not None:
            for key in sorted(self.holds):
                h = self.holds[key]
                self.log("minute", key, h, *self.apply(h))
        self.acc = {"ticks": 0, "mult": 0.0}

    # -- relog and restart
    def disconnect(self):
        self.save_part = self.st["part"] if self.saved else 0.0
        self.online = False

    def connect(self):
        self.st["part"] = self.save_part
        self.online = True

    # -- the bus
    def ask(self, node, cmd, args="", timeout=20):
        self.sleep(0.05)
        side = "server" if node == "server" else "client"
        a = args.split()
        if cmd == "players":
            return ["admin"] if self.online else []
        if cmd == "time.snapshot":
            return {"worldAge": self.age(), "hour": 8, "minutes": 0, "mult": self.mult(), "trueMult": float(self.speed),
                    "wall": self.t * 1000}
        if cmd == "lua.read":
            return self.lua_read(side, a[0], a[1:])
        if cmd == "lua.call":
            return self.lua_call(side, a[0], a[1:])
        if cmd == "bodypart.get":
            if not self.online:
                return "no online player admin"
            parts = [{"index": 7, "name": "Torso_Lower",
                      "additionalPain": (self.st["part"] if side == "server" else self.snap_c.get("part", 0.0))}]
            if a[1] == "all":
                parts = [{"index": i, "additionalPain": (self.st["part"] if i == 7 else self.base_pain.get(i, 0.0))}
                         for i in range(17)]
            return {"ok": True, "side": side, "parts": parts}
        if cmd == "bodypart.set":
            before = self.st["part"]
            self.st["part"] = float(a[3])
            return {"ok": True, "side": side, "part": 7, "field": a[2], "requested": float(a[3]), "before": before,
                    "after": self.st["part"], "synced": len(a) > 4}
        if cmd == "stats.set":
            self.st[a[1]] = float(a[2])
            return {"applied": {a[1]: "Stats:set"}}
        if cmd == "stats.setany":
            self.st[{"UNHAPPINESS": "unhappy", "STRESS": "stress"}[a[1]]] = float(a[2])
            return {"ok": True, "stat": a[1], "side": side, "requested": float(a[2]), "before": 0, "after": float(a[2])}
        if cmd == "stats.all":
            return {"side": side, "user": "admin", "stats": {}, "missing": []}
        if cmd == "ping":
            return "pong"
        return f"unknown command {cmd}"

    def lua_read(self, side, root, paths):
        src = {"TKX_Symptoms.s": self.snap_s, "TKX_Symptoms.c": self.snap_c, "TKX_Symptoms.trk": self.trk,
               "TKX_Symptoms.ctrk": self.ctrk,
               "TKX_Symptoms": {"version": "1"},
               "_G": {"SandboxVars.DayLength": 4 if self.day_min == 90 else 1, "SandboxVars.InjurySeverity": 2,
                      "SandboxVars.Nutrition": False, "SandboxVars.EnduranceRegenMultiplier": 1, "TK.version": 1}}
        node = src.get(root)
        if node is None:
            return {"ok": False, "side": side, "root": root, "error": "root not found"}
        values = {p: node[p] for p in paths if p in node and node[p] is not None}
        return {"ok": True, "side": side, "root": root, "n": len(paths), "values": values, "tables": {}, "types": {},
                "missing": [p for p in paths if p not in values]}

    def lua_call(self, side, path, raw):
        args = []
        for r in raw:
            try:
                args.append(float(r))
            except ValueError:
                args.append({"true": True, "false": False}.get(r, r))
        fn = path.split(".")[-1]
        out = {"ok": True, "side": side, "path": path, "nargs": len(args)}
        r = self.fn(fn, args)
        for i, v in enumerate(r if isinstance(r, tuple) else (r,)):
            if v is not None:
                out[f"r{i + 1}"] = v
        return out

    def fn(self, name, a):
        if name == "watch":
            self.user = a[0]
            return self.online
        if name == "reset":
            self.mlog, self.ring, self.trk = [], [], {"n": 0}
            return True
        if name == "ringOn":
            self.ring_on = a[0] is True
            return self.ring_on
        if name == "cpartSet":
            return True
        if name == "trkReset":
            self.trk = {"n": 0}
            return True
        if name == "creset":
            self.ctrk = {"n": 0}
            return True
        if name == "hold":
            user, kind = a[0], a[1]
            if not self.online:
                return False, "no online player"
            h = {"kind": kind, "part": a[2], "value": a[3]} if kind == "pain" else {"kind": kind, "value": a[2]}
            key = f"pain:{int(a[2])}" if kind == "pain" else kind
            self.user = user
            self.holds[key] = h
            res = self.apply(h)
            self.log("arm", key, h, *res)
            return True, res[0], res[1]
        if name == "release":
            if a[0] == "all":
                n = len(self.holds)
                self.holds = {}
                return True, n
            key = f"pain:{int(a[1])}" if a[0] == "pain" else a[0]
            return self.holds.pop(key, None) is not None
        if name == "setPain":
            before = self.st["part"]
            self.st["part"] = a[2]
            return True, before, self.st["part"]
        if name == "dump":
            self.results[f"tkxs-{a[0]}"] = {"minutes": [dict(r) for r in self.mlog], "mN": len(self.mlog),
                                            "ticks": [dict(r) for r in self.ring], "tN": len(self.ring),
                                            "complete": True}
            return True, len(self.mlog), len(self.ring)
        raise KeyError(name)


def run_session(key, **kw):
    day_min = L.PROFILES[L.SESSIONS[key]["profile"]]["day_min"]
    return run_session_world(key, World(day_min, **kw))


def run_session_world(key, w):
    day_min = w.day_min
    server = FakeServer(w)
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
           "world_changes": {"left_in_place": []}}
    clients = {"admin": FakeClient(w)}
    xs = X.Xs(out, node=lambda side: side if side == "server" else "client", server=server, clients=clients,
              ask=w.ask, budget_s=L.SESSIONS[key]["budget_s"], predictions=L.PRED, clock=w.clock, sleep=w.sleep)

    def launch(S, user, sub):
        w.sleep(40.0)
        w.connect()
        S.xs.clients[user] = FakeClient(w)
        return {"restored": True, "ready_took": 40.0}

    def stop(S):
        w.disconnect()
        w.sleep(10.0)
        return {"exited": True, "rc": 0}

    def restart(S, tag):
        w.lua_reset()
        w.sleep(45.0)
        return {"ok": True}

    S = L.Sess(xs, key, day_min, launch=launch, restart=restart, stop=stop)
    S.body_run(S.phases())
    out["admin_lua_error"] = False
    out["logs"] = {"mod_error": []}
    S.grade_all()
    return {k: v["verdict"] for k, v in out["verdicts"].items()}, out, w


# ================================================================ the sessions against the fake world
@pytest.mark.parametrize("key", ["x491", "x492", "x493"])
def test_faithful_world_grades_every_reading_as_predicted(key):
    verdicts, out, _ = run_session(key)
    assert not out["phase_errors"], out["phase_errors"]
    assert set(verdicts) == set(L.SESSION_GRADES[key])
    assert all(v == "as_predicted" for v in verdicts.values()), {k: (v, out["verdicts"][k]["observed"])
                                                                  for k, v in verdicts.items() if v != "as_predicted"}
    assert out["wall_seconds"] if "wall_seconds" in out else True
    assert not out.get("budget_stop"), out.get("budget_stop")


def test_x491_walls_inside_the_budget():
    _, out, w = run_session("x491")
    assert out["phase_walls"]["C"]["end"] < L.SESSIONS["x491"]["budget_s"] - 80     # the boot's ~80 s on top


def test_x493_walls_inside_the_budget():
    _, out, w = run_session("x493")
    assert out["phase_walls"]["C"]["end"] < L.SESSIONS["x493"]["budget_s"] - 80


def test_x492_walls_and_both_rejoins():
    verdicts, out, w = run_session("x492")
    assert out["readings"]["RELOG"]["back"]["additionalPain"] > 0
    assert out["readings"]["RESTART"]["back"]["additionalPain"] > 0
    assert out["phase_walls"]["C"]["end"] < L.SESSIONS["x492"]["budget_s"] - 80


def test_a_faster_decay_falsifies_the_decay_grades():
    verdicts, _, _ = run_session("x491", decay=0.0045)
    assert verdicts["P2_TICK"] == "falsified" and verdicts["P2_GM"] == "falsified"
    assert verdicts["P2_SPEED"] == "falsified"


def test_a_faster_rise_falsifies_the_rise():
    verdicts, _, _ = run_session("x491", rise_div=400.0)
    assert verdicts["P1_RISE"] == "falsified"


def test_a_lost_save_falsifies_the_persistence():
    verdicts, out, _ = run_session("x492", saved=False)
    assert verdicts["P3_RELOG"] == "falsified" and verdicts["P3_RESTART"] == "falsified"
    assert out["verdicts"]["P3_RELOG"]["observed"]["state"] == "lost"


def test_a_shifted_client_level_falsifies_the_level_grades():
    v1, _, _ = run_session("x491", client_level_shift=1)
    assert v1["P1_STEADY_A1"] == "falsified" and v1["P1_FOLLOWS"] == "falsified"
    v3, _, _ = run_session("x493", client_level_shift=1)
    assert v3["P4_LEVEL_0.74"] == "falsified" and v3["P5_U25"] == "falsified" and v3["P5_S55"] == "falsified"


def test_a_worst_case_overshoot_falsifies_the_climb_and_no_climb_keeps_the_tight_cap():
    v, _, _ = run_session("x493", regen=L.END_REGEN_UNIT * 1.5)
    assert v["P4_CLIMB"] == "falsified"
    v0, out0, _ = run_session("x493", regen=0.0)
    assert v0["P4_CLIMB"] == "falsified"                          # a climb must be above 0
    assert v0["P4_TIGHT"] == "as_predicted"                       # no climb: no flip predicted, none seen
    assert out0["verdicts"]["P4_TIGHT"]["observed"]["flip_predicted"] is False


def test_the_tight_cap_flips_in_the_faithful_world():
    _, out, _ = run_session("x493")
    o = out["verdicts"]["P4_TIGHT"]["observed"]
    assert o["flip_predicted"] is True and o["flip_seen"] is True


# ================================================================ the pure grades: levels
def test_level_of_matches_the_jar_thresholds():
    assert [L.level_of("pain", v) for v in (10, 10.01, 20, 20.5, 50.1, 75.1)] == [0, 1, 1, 2, 3, 4]
    assert [L.level_of("unhappy", v) for v in (20, 25, 45.5, 60.5, 81)] == [0, 1, 2, 3, 4]
    assert [L.level_of("stress", v) for v in (0.25, 0.3, 0.55, 0.8, 0.95, 1.5)] == [0, 1, 2, 3, 4, 4]
    assert [L.level_of("endurance", v) for v in (1, 0.751, 0.75, 0.5, 0.26, 0.11, 0.1, 0)] == [0, 0, 1, 2, 2, 3, 4, 4]
    assert L.level_of("pain", None) is None
    assert L.level_of("pain", L.pain_target(L.A1)) == 1 and L.level_of("pain", L.pain_target(L.A2)) == 2
    assert L.level_of("pain", L.pain_target(L.A1 - L.dip_per_gm(90))) == 1      # the dip stays inside the level


def test_the_schedule_values_sit_inside_their_levels_with_margin():
    for cap, want in L.END_WANT.items():
        assert L.level_of("endurance", cap) == want
    for cap in L.END_CAPS:
        if cap != L.END_TIGHT:      # the normal climb a 90-minute game minute (0.0056) stays inside the level
            assert L.level_of("endurance", cap + L.END_REGEN_BASE * 180) == L.END_WANT[cap]
    assert L.level_of("endurance", L.END_TIGHT + L.END_REGEN_BASE * 180) == 0
    assert all(L.level_of("unhappy", f) == w for f, w in L.UNHAPPY_WANT.items())
    assert all(L.level_of("stress", f) == w for f, w in L.STRESS_WANT.items())


def pair(tag, arm, s, c, valid=True):
    return {"tag": tag, "arm": arm, "s": dict(s, online=True), "c": c, "valid": valid}


def test_make_pair_needs_both_reads_inside_the_gap_and_online():
    s, c = {"online": True, "pain": 1}, {"pain": 1}
    assert L.make_pair("t", "A", s, 10.0, c, 10.9)["valid"] is True
    assert L.make_pair("t", "A", s, 10.0, c, 11.2)["valid"] is False
    assert L.make_pair("t", "A", {"online": False}, 10.0, c, 10.1)["valid"] is False
    assert L.make_pair("t", "A", s, None, c, 10.1)["valid"] is False
    assert L.make_pair("t", "A", {}, 10.0, c, 10.1)["valid"] is False


def test_grade_steady_cases():
    good = [pair(str(i), "A", {"lvPain": 1}, {"lvPain": 1}) for i in range(6)]
    assert L.grade_steady(good, "A", "lvPain", 1)[0] == "as_predicted"
    bad = good[:-1] + [pair("x", "A", {"lvPain": 1}, {"lvPain": 0})]
    assert L.grade_steady(bad, "A", "lvPain", 1)[0] == "falsified"
    assert L.grade_steady(good[:3], "A", "lvPain", 1)[0] == "unmeasured"
    assert L.grade_steady(good, "B", "lvPain", 1)[0] == "unmeasured"


def test_grade_target_cases():
    t = L.pain_target(L.A1)
    ok = [pair("a", "A", {"pain": t - 0.5}, {})]
    assert L.grade_target(ok, "A", L.A1, 90)[0] == "as_predicted"
    assert L.grade_target([pair("a", "A", {"pain": 0.8 * t}, {})], "A", L.A1, 90)[0] == "falsified"
    assert L.grade_target([pair("a", "A", {"pain": t + 0.1}, {})], "A", L.A1, 90)[0] == "falsified"
    assert L.grade_target([], "A", L.A1, 90)[0] == "unmeasured"


def test_grade_follows_cases():
    ps = [pair("a", "A", {"pain": 15, "lvPain": 1}, {"pain": 25, "lvPain": 2}),
          pair("b", "A", {"pain": 10.5, "lvPain": 0}, {"pain": 10.4, "lvPain": 0})]       # near 10: excluded
    v, o, used = L.grade_follows(ps, ("A",), "pain", "pain", "lvPain", L.FOLLOW_EPS)
    assert v == "as_predicted" and o["n"] == 2
    ps.append(pair("c", "A", {"pain": 30, "lvPain": 2}, {"pain": 30, "lvPain": 1}))
    assert L.grade_follows(ps, ("A",), "pain", "pain", "lvPain", L.FOLLOW_EPS)[0] == "falsified"
    assert L.grade_follows(ps, ("Z",), "pain", "pain", "lvPain", L.FOLLOW_EPS)[0] == "unmeasured"
    st = [pair("s", "A", {"stress": 0.2, "nicotine": 0.1, "lvStress": 1}, {"stress": 0.2, "nicotine": 0.1,
                                                                            "lvStress": 1})]
    assert L.grade_follows(st, ("A",), "stress", "stress", "lvStress", 0.01, "nicotine")[0] == "as_predicted"


def ticks_rise(div, n=80, part=20.0):
    out, pain = [], 0.0
    mod = L.PAIN_MOD[7]
    for i in range(n):
        out.append({"n": i, "pain": pain, "part": part})
        pain += (mod * part - pain) / div
    return out


def test_grade_rise_cases():
    assert L.grade_rise(ticks_rise(500.0))[0] == "as_predicted"
    assert L.grade_rise(ticks_rise(300.0))[0] == "falsified"
    assert L.grade_rise(ticks_rise(500.0, n=20))[0] == "unmeasured"
    gappy = [dict(t, n=t["n"] * 2) for t in ticks_rise(500.0)]        # no two consecutive ticks
    assert L.grade_rise(gappy)[0] == "unmeasured"


def mrows(value, falls, mult=180.0, ticks=37, dt_gm=1.0, ev0="minute"):
    rows, age = [], 10.0
    rows.append({"ev": ev0, "after": value, "before": value, "mult": mult, "ticks": ticks, "age": age})
    for f in falls:
        age += dt_gm / 60.0
        rows.append({"ev": "minute", "after": value, "before": value - f, "mult": mult, "ticks": ticks, "age": age})
    return rows


def test_grade_decay_tick_cases():
    good = mrows(40.0, [0.9] * 6)
    assert L.grade_decay_tick([good])[0] == "as_predicted"
    assert L.grade_decay_tick([mrows(40.0, [0.9] * 5 + [0.8])])[0] == "falsified"
    assert L.grade_decay_tick([mrows(40.0, [0.9] * 3)])[0] == "unmeasured"
    armed = mrows(40.0, [0.5] + [0.9] * 6, ev0="arm")              # the gap after an arm is not graded
    assert L.grade_decay_tick([armed])[0] == "as_predicted"


def test_grade_decay_gm_cases():
    assert L.grade_decay_gm([mrows(40.0, [0.9] * 6)], 90)[0] == "as_predicted"
    assert L.grade_decay_gm([mrows(40.0, [0.95] * 6)], 90)[0] == "falsified"
    assert L.grade_decay_gm([mrows(40.0, [0.15] * 6, mult=30.0)], 15)[0] == "as_predicted"
    assert L.grade_decay_gm([mrows(40.0, [0.9] * 6)], 15)[0] == "falsified"
    assert L.grade_decay_gm([mrows(40.0, [0.9] * 2)], 90)[0] == "unmeasured"
    two = [mrows(20.0, [0.9] * 3), mrows(40.0, [0.9] * 3)]          # two windows pool, never pair across
    assert L.grade_decay_gm(two, 90)[0] == "as_predicted" and len(L.gaps(two)) == 6


def test_grade_snap_cases():
    mod = L.PAIN_MOD[7]
    ticks = [{"n": i, "part": 30 - 0.024 * i, "pain": mod * (30 - 0.024 * i)} for i in range(40)]
    assert L.grade_snap(ticks)[0] == "as_predicted"
    lag = [dict(t, pain=t["pain"] + 0.2) if t["n"] > 20 else t for t in ticks]
    assert L.grade_snap(lag)[0] == "falsified"
    assert L.grade_snap(ticks[:5])[0] == "unmeasured"
    under = [dict(t, pain=t["pain"] - 1) for t in ticks]                  # never reaches the target: unmeasured
    assert L.grade_snap(under)[0] == "unmeasured"


def test_grade_persist_cases():
    assert L.grade_persist(60.0, 55.0)[0] == "as_predicted"
    v, o, _ = L.grade_persist(60.0, 0.0)
    assert v == "falsified" and o["state"] == "lost"
    assert L.grade_persist(60.0, 10.0)[1]["state"] == "partial"
    assert L.grade_persist(None, 50.0)[0] == "unmeasured"
    assert L.grade_persist(60.0, None)[0] == "unmeasured"
    assert L.grade_persist(0.0, 0.0)[0] == "unmeasured"


def test_grade_hold_level_cases():
    ps = [pair(str(i), "E", {"lvEnd": 2}, {"lvEnd": 2}) for i in range(4)]
    trk = {"n": 100, "lvEndMin": 2, "lvEndMax": 2}
    assert L.grade_hold_level(ps, "E", "lvEnd", 2, trk, trk)[0] == "as_predicted"
    assert L.grade_hold_level(ps, "E", "lvEnd", 2, trk, dict(trk, lvEndMin=1))[0] == "falsified"
    assert L.grade_hold_level(ps[:3] + [pair("x", "E", {"lvEnd": 3}, {"lvEnd": 2})], "E", "lvEnd", 2, trk,
                              trk)[0] == "falsified"
    assert L.grade_hold_level(ps[:2], "E", "lvEnd", 2, trk, trk)[0] == "unmeasured"
    assert L.grade_hold_level(ps, "E", "lvEnd", 2, {"n": 0}, trk)[0] == "unmeasured"


def crows(cap, climbs, mult=180.0):
    rows = [{"ev": "minute", "after": cap, "before": cap, "mult": mult}]
    for c in climbs:
        rows.append({"ev": "minute", "after": cap, "before": cap + c, "mult": mult})
    return rows


def test_grade_tight_cases():
    rows = crows(0.748, [0.0056] * 5)
    assert L.grade_tight({"n": 50, "lvEndMin": 0, "lvEndMax": 1}, rows, 0.002)[0] == "as_predicted"
    assert L.grade_tight({"n": 50, "lvEndMin": 1, "lvEndMax": 1}, rows, 0.002)[0] == "falsified"
    slow = crows(0.748, [0.001] * 5)
    assert L.grade_tight({"n": 50, "lvEndMin": 1, "lvEndMax": 1}, slow, 0.002)[0] == "as_predicted"
    assert L.grade_tight({"n": 50, "lvEndMin": 0, "lvEndMax": 1}, slow, 0.002)[0] == "falsified"
    assert L.grade_tight({"n": 0}, rows, 0.002)[0] == "unmeasured"
    assert L.grade_tight({"n": 50, "lvEndMin": 0}, [], 0.002)[0] == "unmeasured"


def test_grade_climb_cases():
    ok = L.climbs([crows(0.74, [0.0056] * 4)])
    assert L.grade_climb(ok)[0] == "as_predicted"
    assert L.grade_climb(L.climbs([crows(0.74, [0.0056] * 3 + [0.02])]))[0] == "falsified"
    assert L.grade_climb(L.climbs([crows(0.74, [0.0056] * 3 + [0.0])]))[0] == "falsified"
    assert L.grade_climb(L.climbs([crows(0.74, [0.0056] * 2)]))[0] == "unmeasured"


def test_grade_base_cases():
    p = {"valid": True, "s": {"pain": 0.0, "stress": 0.0, "nicotine": 0.0, "unhappy": 0.0, "endurance": 1.0}}
    parts = {"ok": True, "parts": [{"index": i, "additionalPain": 0.0} for i in range(17)]}
    assert L.grade_base(p, parts)[0] == "as_predicted"
    assert L.grade_base(p, {"parts": [{"index": 3, "additionalPain": 4.0}]})[0] == "falsified"
    assert L.grade_base(dict(p, s=dict(p["s"], unhappy=21.0)), parts)[0] == "falsified"
    assert L.grade_base(dict(p, s=dict(p["s"], stress=0.2, nicotine=0.1)), parts)[0] == "falsified"
    assert L.grade_base(dict(p, s=dict(p["s"], endurance=0.7)), parts)[0] == "falsified"
    assert L.grade_base(dict(p, valid=False), parts)[0] == "unmeasured"
    assert L.grade_base(p, "no online player admin")[0] == "unmeasured"


def test_a_pained_first_sight_falsifies_the_base_precondition():
    day_min = 90
    v, _, _ = run_session_world("x491", World(day_min))
    assert v["P0_BASE"] == "as_predicted"
    w = World(day_min)
    w.base_pain = {3: 5.0}
    v2, _, _ = run_session_world("x491", w)
    assert v2["P0_BASE"] == "falsified"


def test_grade_z_cases():
    assert L.grade_z([], False, {})[0] == "as_predicted"
    assert L.grade_z(["TKX_Symptoms_Server.lua:12 attempted index"], False, {})[0] == "falsified"
    assert L.grade_z([], True, {})[0] == "falsified"
    assert L.grade_z([], False, {"S.server": "boom"})[0] == "falsified"
    assert L.grade_z([], None, {})[0] == "unmeasured"


def test_combine_cases():
    a, f, u = ("as_predicted", 1, [1]), ("falsified", 2, [2]), ("unmeasured", 3, [])
    assert L.combine([a, a])[0] == "as_predicted"
    assert L.combine([a, f])[0] == "falsified"
    assert L.combine([a, u])[0] == "unmeasured"
    assert L.combine([])[0] == "unmeasured"


def test_zero_samples_never_pass_through_the_recorder():
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}}
    xs = X.Xs(out, node=lambda s: s)
    xs.grade("P", "as_predicted", {}, "f", samples=[])
    assert out["verdicts"]["P"]["verdict"] == "unmeasured"


# ================================================================ the pre-boot checks and the drivers
def test_preboot_passes_for_every_session():
    for key, spec in L.SESSIONS.items():
        c, ok = L.preboot(key, spec["driver"])
        assert ok, c


def test_preboot_refuses_a_wrong_driver_or_session():
    assert L.preboot("x491", "x492_persist.py")[1] is False
    assert L.preboot("x499", "x499_levers.py")[1] is False


def test_profile_doc_checks_fail_on_each_mutation():
    import tomllib
    name = "x49-levers"
    text = open(os.path.join(REPO, "testing", "profiles", name + ".toml"), encoding="utf-8").read()
    doc = tomllib.loads(text)
    assert all(L.profile_doc_checks(name, doc, text).values())
    muts = [
        ("fixture", "two"), ("clients", ["admin", "bob"]),
    ]
    for k, v in muts:
        d = dict(doc, **{k: v})
        assert not all(L.profile_doc_checks(name, d, text).values()), k
    assert not all(L.profile_doc_checks(name, dict(doc, sandbox={"Nutrition": True, "DayLength": 4}), text).values())
    assert not all(L.profile_doc_checks(name, dict(doc, sandbox={"Nutrition": False, "DayLength": 1}), text).values())
    assert not all(L.profile_doc_checks(name, dict(doc, server={"SleepAllowed": False, "SleepNeeded": True}),
                                        text).values())
    nr = dict(doc, mods=doc["mods"] + [{"id": "NutritionRevamp", "path": "release/x"}])
    assert not all(L.profile_doc_checks(name, nr, text).values())
    assert not all(L.profile_doc_checks(name, doc, "# another header").values())
    assert not all(L.profile_doc_checks(name, dict(doc, verify=doc["verify"][:1]), text).values())
    assert L.profile_doc_checks("x00", doc, text) == {"known_profile": False}


def test_markers_fail_on_a_missing_marker(tmp_path):
    files = {"a.lua": "a.lua"}
    (tmp_path / "a.lua").write_text("function T.hold(", encoding="utf-8")
    assert L.markers_ok(files, {"a.lua": ("function T.hold(",)}, str(tmp_path))[1] is True
    assert L.markers_ok(files, {"a.lua": ("function T.dump(",)}, str(tmp_path))[1] is False
    assert L.markers_ok({"b.lua": "b.lua"}, {"b.lua": ("x",)}, str(tmp_path))[1] is False


def test_parse_argv_refuses_any_argument():
    assert L.parse_argv([], "x491_levers.py") is None
    assert "takes no arguments" in L.parse_argv(["--fast"], "x491_levers.py")


@pytest.mark.parametrize("key", ["x491", "x492", "x493"])
def test_each_driver_names_its_session_and_refuses_before_booting(key):
    src = open(os.path.join(EXP, L.SESSIONS[key]["driver"]), encoding="utf-8").read()
    assert f'KEY = "{key}"' in src and f'PREFIX = "{key}"' in src
    i_ref, i_main = src.index("L.parse_argv(sys.argv[1:]"), src.index("L.main(KEY")
    assert i_ref < i_main and "sys.exit(refusal)" in src[i_ref:i_main]


def test_each_session_has_a_prediction_and_a_falsifier_per_grade():
    for key, names in L.SESSION_GRADES.items():
        for n in names:
            assert n in L.PRED, n
