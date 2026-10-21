"""Offline tests of testing/experiments/x49b_lib.py, x49b_prerun.py and x494_accept.py (Plan 18 Task 4, run x494):
every grade with a failing case and its unmeasured case; the effects in force and the progress placement; the
pre-boot checks on the real repository, the real re-staged upload copy, the real probe and the real fixture; the prerun
current at HEAD; the driver's refusal and predictions; and x494's body run against a fake world behind a fake bus,
once as predicted and once per defect flag that must move a named grade off as_predicted.

The fake world is test_x48_lib's World (the mod itself on the replay host, stepped a game minute at a time as the fake
clock passes, the ring row read before each drain, the harness's real reply shapes) from the first sight with no typed
weight (the creation body), at x494's options, with vanilla's physics between the mod's writes laid over it tick by
tick (TICK_S of wall): added pain falls 0.005 a multiplier unit (J3), ENDURANCE climbs CLIMB_GM a game minute (x493's
T91.22), STRESS falls STRESS_DECAY_GM a game minute (T91.25), PAIN rises 1/500 of its gap a server tick at 10 a second
and is set at once when the target is lower (#2362), the Pain moodle recomputes once every 120 server ticks or client
frames (60 a second) and the other levels every tick (J9), and the probe's snapshots and trackers read it all on both
sides. The fake has no Stress-2 UNHAPPINESS rise (#3016) and no BORED term; the live tolerances cover them (the floors
are at-or-over grades, UNHAPPY_DROP_TOL holds a minute's rise). A defect flag patches the mod (a kernel wrap, as a mod defect would) or the world (a lost part, a stale client,
a slow moodle, no stress decay). The grading replays the real HEAD replay against the fake ring, so the as-predicted
run also checks the write placement, the stat events and the replay inputs end to end.

The fake bus answers the harness's real reply shapes (docs/reference/harness-commands.md, the handlers' @reply lines):
test_x48_lib's, plus lua.read of a probe table {ok, side, root, n, values, tables, types, missing}; lua.call {ok, side,
path, nargs, r1, r2, r3}; stats.setany {ok, stat, side, requested, before, after}; bodypart.get {ok, side, parts} with
each row {index, name, additionalPain}. The staged-copy and fixture tests skip where release/ or the fixture cache
(both gitignored) are absent.
"""
import json
import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
EXP = os.path.join(os.path.dirname(HERE), "experiments")
sys.path.insert(0, EXP)

import x49b_lib as L                  # noqa: E402
import x49b_prerun as PR              # noqa: E402
import x48_lib as L48                 # noqa: E402
import x49_lib as L49                 # noqa: E402
import xlib as X                      # noqa: E402
import replay_live as RL              # noqa: E402
import test_x48_lib as T48            # noqa: E402

REPO = L.REPO
need_staged = pytest.mark.skipif(not os.path.isdir(os.path.join(REPO, L.STAGE_ROOT)),
                                 reason="release/ (gitignored) not staged on this machine")
need_fixture = pytest.mark.skipif(not os.path.isfile(os.path.join(REPO, L48.FIXTURE_PLAYERS_DB)),
                                  reason="the default fixture cache is not provisioned on this machine")

TICK_S = 0.1
CLIMB_GM = 0.0066                      # x493-20261021-062610's climb a game minute at the 90-minute day (T91.22)
PART_ORDER = ("Hand_L", "Hand_R", "ForeArm_L", "ForeArm_R", "UpperArm_L", "UpperArm_R", "Torso_Upper", "Torso_Lower",
              "Head", "Neck", "Groin", "UpperLeg_L", "UpperLeg_R", "LowerLeg_L", "LowerLeg_R", "Foot_L", "Foot_R")
LEVEL_KEYS = {"lvPain": "pain", "lvEnd": "endurance", "lvStress": "stress", "lvUnhappy": "unhappy"}

# a mod defect as a kernel wrap (the adapters call through the kernel's tables each minute)
WRAP = ("local K = NutritionRevamp.kernel; local s0 = K.effects.symptoms; "
        "K.effects.symptoms = function(E, T, D, sev, overlay, dayMin) s0(E, T, D, sev, overlay, dayMin); %s end")
PATCH = {
    "no_floors": WRAP % "E.stressFloor = 0; E.unhappyFloor = 0",
    "no_cap": WRAP % "E.symCap = 1; E.enduranceCap = E.rowEndCap",
    "pain_kept": WRAP % ("if D.frac[1] ~= nil and E.pain[7] == 0 then E.pain[7] = 19.680769230769; "
                         "E.painOn = true end"),
    "no_ease": ("local K = NutritionRevamp.kernel; local m0 = K.drain.smooth; "
                "K.drain.smooth = function(D, body, ageH, active) local p0 = D.pS; local p, c = m0(D, body, ageH, active); "
                "if not active and p0 > D.pS then D.pS = p0 end; return D.pS, c end"),
    "no_subtract": ("local K = NutritionRevamp.kernel; local f0 = K.hybrid.floor; "
                    "K.hybrid.floor = function(v0, ut, last, rise) return f0(v0, ut, math.min(last, ut), rise) end"),
    "no_beri_pain": WRAP % "E.pain[13] = 0; E.pain[14] = 0",
    # the writer ignoring a floor the effects carry (W.monotony runs right after the STRESS target's line)
    "no_u_target": ("local W = NutritionRevamp.server.writer; local m0 = W.monotony; "
                    "W.monotony = function(h, record, inp, E, ageH) local uf = E.unhappyFloor; E.unhappyFloor = 0; "
                    "m0(h, record, inp, E, ageH); E.unhappyFloor = uf end"),
    "heal_over": ("local K = NutritionRevamp.kernel; local h0 = K.drain.heal; "
                  "K.drain.heal = function(D, health, y, dtM) local v = h0(D, health, y, dtM); "
                  "if v > 0 then return v + 20 end; return v end"),
    "half_take": ("local D0 = NutritionRevamp.kernel.drain; local t0 = D0.take; "
                  "D0.take = function(D, h) return 0.5 * t0(D, h) end"),
    "no_s_target": ("local W = NutritionRevamp.server.writer; local m0 = W.monotony; "
                    "W.monotony = function(h, record, inp, E, ageH) inp.stressTarget = math.max(0, E.stressTarget or 0); "
                    "m0(h, record, inp, E, ageH) end"),
}


class World(T48.World):
    """test_x48_lib's World at x494's options from the first sight with no typed weight, vanilla's physics laid over it
    tick by tick, and the probe's snapshots and trackers on both sides."""

    def __init__(self, results_dir, flags=()):
        self.dir = results_dir
        self.f = set(flags)
        prof = L.PROFILES["x49-accept"]
        self.be = RL.ServerReplay(hour_offset=L48.HOUR_OFFSET, rng="half", sleep_allowed=False,
                                  stats=dict(L48.FIRST_SIGHT["stats"]), player=dict(PR.FIRST_SIGHT_PLAYER),
                                  death_pace=prof["pace"], health_combine=prof["combine"], day_minutes=L.DAY_MIN,
                                  game_heal=True)
        T48.lua51 = self.be.lua51
        for k, src in PATCH.items():
            if k in self.f:
                self.be.rt.execute(src)
        rt = self.be.rt
        self._parts = rt.eval("function() local o = {} for _, p in ipairs(NR_T.painParts) do o[p.name] = p.addPain "
                              "end return o end")
        self._decay = rt.eval("function(d) NR_T.decayPain(d) end")
        self._zero = rt.eval("function() for _, p in ipairs(NR_T.painParts) do p.addPain = 0 end end")
        self.t, self.speed = 0.0, 1.0
        self.age = L48.FIRST_SIGHT["age"] - 1.0 / 60.0
        self.k = 0
        self.ring, self.ring_on, self.paths, self.s = [], False, [], 0
        self.delayed = []
        self.dead = False
        self.saves = 0
        self.pain, self.n, self.frames = 0.0, 0.0, 0.0
        self.lv_s = {k: 0 for k in LEVEL_KEYS}
        self.lv_c = {k: 0 for k in LEVEL_KEYS}
        self.trk_s, self.trk_c = {"n": 0, "ms": 0.0}, {"n": 0, "ms": 0.0}
        rt.execute("SandboxVars = SandboxVars or {}; SandboxVars.NR = SandboxVars.NR or {}; "
                   "SandboxVars.NR.Severity = 1.0")                # the profile's, written into the options file
        self.step_minute()                                     # the first sight
        self.levels(server=True, client=True, pain=True)

    # -- the clock, tick by tick
    def sleep(self, dt):
        end = self.t + dt
        while self.t < end:
            if end - self.t < 1e-9:                            # a float crumb: land on end (a loop's own end test)
                self.age += (end - self.t) * self.speed / self.GH_S
                self.t = end
                return
            nxt = (math.floor(self.age * 60.0 + 1e-9) + 1) / 60.0
            step = min(TICK_S, end - self.t)
            d_age = step * self.speed / self.GH_S
            if self.age + d_age >= nxt - 1e-12:
                self.tick((nxt - self.age) * self.GH_S / self.speed)
                self.age = nxt
                self.step_minute()
            else:
                self.tick(step)
                self.age += d_age

    def part_values(self):
        p = self._parts()
        return {i: float(p[name] or 0.0) for i, name in enumerate(PART_ORDER)}

    def levels(self, server, client, pain):
        sv = self.be.p.sv
        val = {"lvPain": self.pain, "lvEnd": sv["ENDURANCE"], "lvStress": (sv["STRESS"] or 0.0),
               "lvUnhappy": (sv["UNHAPPINESS"] or 0.0)}
        for key, kind in LEVEL_KEYS.items():
            if key == "lvPain" and not pain:
                continue
            lv = L49.level_of(kind, val[key])
            if server:
                self.lv_s[key] = lv
            if client and "client_stale" not in self.f:
                self.lv_c[key] = lv

    def track(self):
        for trk, lv in ((self.trk_s, self.lv_s), (self.trk_c, self.lv_c)):
            for key, v in lv.items():
                if trk.get(key + "Min") is None or v < trk[key + "Min"]:
                    trk[key + "Min"] = v
                if trk.get(key + "Max") is None or v > trk[key + "Max"]:
                    trk[key + "Max"] = v
            trk["n"] += 1

    def tick(self, step):
        self.t += step
        gm = step * self.speed / self.GH_S * 60.0
        sv = self.be.p.sv
        if "pain_lost" in self.f:
            self._zero()
        else:
            self._decay(L.dip_gm() * gm)
        sv["ENDURANCE"] = min(1.0, sv["ENDURANCE"] + CLIMB_GM * gm)
        if "no_stress_decay" not in self.f:
            sv["STRESS"] = max(0.0, (sv["STRESS"] or 0.0) - L.STRESS_DECAY_GM * gm)
        parts = self.part_values()
        tgt = sum(L.PAIN_MOD[i] * parts[i] for i in L.PAIN_PARTS)
        nt = step * L.TICK_HZ_NOM
        if tgt > self.pain:
            self.pain = tgt - (tgt - self.pain) * (1.0 - 1.0 / L.RISE_DIV) ** nt
        else:
            self.pain = tgt
        timer = L.PAIN_TIMER_UPDATES * (7 if "slow_moodle" in self.f else 1)
        n0, f0 = self.n, self.frames
        self.n += nt
        self.frames += step * L.CLIENT_FPS_NOM
        self.levels(server=True, client=True, pain=False)
        if math.floor(self.n / timer) > math.floor(n0 / timer):
            self.levels(server=True, client=False, pain=True)
        if math.floor(self.frames / timer) > math.floor(f0 / timer) and "client_stale" not in self.f:
            self.lv_c["lvPain"] = L49.level_of("pain", self.pain)
        self.track()

    # -- the probe
    def snap_s(self):
        sv, parts = self.be.p.sv, self.part_values()
        d = {"online": True, "n": int(self.n), "ms": self.t * 1000.0, "age": self.age, "mult": self.speed * 4.75,
             "trackPart": 7, "pain": self.pain, "part": parts[7], "endurance": sv["ENDURANCE"],
             "stress": sv["STRESS"] or 0.0, "nicotine": 0.0, "unhappy": sv["UNHAPPINESS"] or 0.0,
             "boredom": sv["BOREDOM"] or 0.0, "fatigue": sv["FATIGUE"]}
        d.update(self.lv_s)
        return d

    def snap_c(self):
        sv, parts = self.be.p.sv, self.part_values()
        d = {"n": int(self.frames), "ms": self.t * 1000.0, "cpart": 7, "pain": self.pain, "part": parts[7],
             "endurance": sv["ENDURANCE"], "stress": sv["STRESS"] or 0.0, "nicotine": 0.0,
             "unhappy": sv["UNHAPPINESS"] or 0.0, "boredom": sv["BOREDOM"] or 0.0}
        d.update(self.lv_c)
        return d

    def probe_read(self, root, paths, client):
        src = {"TKX_Symptoms.s": self.snap_s, "TKX_Symptoms.c": self.snap_c,
               "TKX_Symptoms.trk": lambda: dict(self.trk_s), "TKX_Symptoms.ctrk": lambda: dict(self.trk_c),
               "TKX_Symptoms": lambda: {"version": "1"}}[root]()
        values = {p: src[p] for p in paths if src.get(p) is not None}
        return {"ok": True, "side": "client" if client else "server", "root": root, "n": len(paths), "values": values,
                "tables": {}, "types": {p: type(v).__name__ for p, v in values.items()},
                "missing": {p: "nil" for p in paths if p not in values}}

    def ask(self, node, cmd, args="", timeout=30):
        a = args.split() if isinstance(args, str) else list(args)
        client = node == L.CLIENT
        if cmd == "lua.read" and a and a[0].startswith("TKX_Symptoms"):
            return self.probe_read(a[0], a[1:], client)
        if cmd == "lua.call":
            fn = a[0].split(".")[-1]
            if fn == "trkReset":
                self.trk_s = {"n": 0, "ms": self.t * 1000.0}
            elif fn == "creset":
                self.trk_c = {"n": 0, "ms": self.t * 1000.0}
            return {"ok": True, "side": "client" if client else "server", "path": a[0], "nargs": len(a) - 1,
                    "r1": True}
        if cmd == "stats.setany":
            stat, v = a[1], float(a[2])
            sv = self.be.p.sv
            before = sv[stat]
            sv[stat] = v
            return {"ok": True, "stat": stat, "side": "server", "requested": v, "before": before, "after": sv[stat]}
        if cmd == "record.set" and "no_lapse" in self.f and a[1] == "satiety.M" and float(a[2]) > 0:
            ok, before = self.walk("satiety.M")
            return {"ok": True, "side": "server", "user": a[0], "path": a[1], "key": "M", "keyType": "string",
                    "before": before, "beforeType": "number", "after": before, "afterType": "number"}
        if cmd == "bodypart.get":
            pv = self.part_values()
            idx = range(17) if a[1] == "all" else [int(a[1])]
            return {"ok": True, "side": "server", "parts": [{"index": i, "name": PART_ORDER[i],
                                                             "additionalPain": pv[i]} for i in idx]}
        return super().ask(node, cmd, args, timeout)


def run_session(tmp_path, flags=(), budget=1e9):
    d = str(tmp_path)
    os.makedirs(d, exist_ok=True)
    w = World(d, flags)
    T48.fake_lread_saves(w)
    out = T48.fresh_out()
    xs = X.Xs(out, node=lambda side: side, clients={"admin": T48.FakeClient("admin")}, ask=w.ask, budget_s=budget,
              clock=w.clock, sleep=w.sleep, spawn_wait_s=0.5)
    xs.server = T48.FakeServer(w, d)
    S = L.Sess(xs, "x494", run_dir=d)
    for _ in range(int(0.25 * 60)):                            # the boot's game time before S, as live
        w.sleep(w.GH_S / 60.0)
    S.body_run(S.phases())
    out["logs"] = {"mod_error": []}
    out["admin_lua_error"] = False
    S.grade_all()
    v = {k: x["verdict"] for k, x in out["verdicts"].items()}
    return v, out, w, S


def bad(v, out):
    return {k: (x, out["verdicts"][k]["observed"]) for k, x in v.items() if x != "as_predicted"}


NAMES = ({"OPT", "ONSET", "P0_BASE", "BERI_ON", "H1", "RING", "Z", "PAIN_PART", "PAIN_TARGET", "PAIN_ONSET",
          "PAIN_LEVELS", "PAIN_FOLLOWS", "END_CAP", "END_LEVELS", "STRESS_FLOOR", "UNHAPPY_FLOOR", "STRESS_LEVELS",
          "UNHAPPY_LEVELS", "REL_LAPSE", "REL_PAIN", "REL_END", "REL_UNHAPPY", "REL_STRESS", "REL_HEAL"}
         | {f"REPLAY_{f}" for f in L.REPLAY_TOL})


@pytest.fixture(scope="module")
def as_predicted(tmp_path_factory):
    return run_session(tmp_path_factory.mktemp("x494"))


def test_x494_as_predicted(as_predicted):
    v, out, w, S = as_predicted
    assert set(v) == NAMES
    assert not bad(v, out), bad(v, out)
    assert not out["phase_errors"] and not out.get("skipped_phases")
    assert list(out["phase_walls"]) == ["S", "H", "W", "A", "ON", "P1", "B", "P2", "L", "C", "R"]


def test_x494_reads_as_its_prerun(as_predicted):
    v, out, w, S = as_predicted
    p = L.load_prerun()["x494"]
    want = {k: p["arms"][k]["levels"] for k in ("P1", "B", "P2", "L2")}
    pl = out["verdicts"]["PAIN_LEVELS"]["observed"]
    assert {k: pl[k]["want"] for k in want} == {k: x["pain"] for k, x in want.items()}
    el = out["verdicts"]["END_LEVELS"]["observed"]
    assert {k: el[k]["want"] for k in ("P1", "B", "P2")} == {k: want[k]["endurance"] for k in ("P1", "B", "P2")}
    assert el["ON"]["want"] == 1
    for name, kind in (("STRESS_LEVELS", "stress"), ("UNHAPPY_LEVELS", "unhappy")):
        o = out["verdicts"][name]["observed"]
        assert {k: o[k]["want"] for k in ("P1", "B", "P2")} == {k: want[k][kind] for k in ("P1", "B", "P2")}
    lp = out["verdicts"]["REL_LAPSE"]["observed"]
    assert lp["mask"] == p["lapse"]["mask"] and lp["lag_gm"] <= L.LAPSE_GM
    ru = out["verdicts"]["REL_UNHAPPY"]["observed"]
    assert ru["fall"] == pytest.approx(p["lapse"]["u_before"] - p["lapse"]["u_after"], abs=0.05)
    # the floor seeds read the record's floors, placed as stat events
    assert [round(st["value"], 6) for st in out["stat_sets"]] == [0.3, 25.0, 0.55, 50.0]
    assert out["replay"]["fields"]["moodLast.u"]["n"] > 50 and out["replay"]["fields_after_lapse"]["moodLast.u"]["n"] > 50
    assert out["replay"]["fields_after_lapse"].get("health") is None          # health graded to the lapse row (F2)
    assert out["verdicts"]["REL_HEAL"]["observed"]["last_gap"] == pytest.approx(0.0, abs=L.REL_HEAL_TOL)
    assert all(b["how"] == "progress" for b in out["model_inputs"]["placement"] if b.get("path") == "drain.pS")


FLAGS = [
    ("no_floors", {"STRESS_FLOOR", "STRESS_LEVELS", "UNHAPPY_LEVELS", "REPLAY_effects.stressFloor",
                   "REPLAY_effects.unhappyFloor", "REPLAY_moodLast.u", "REL_UNHAPPY"}),
    ("no_u_target", {"UNHAPPY_FLOOR", "REPLAY_moodLast.u", "REL_UNHAPPY"}),
    ("no_s_target", {"STRESS_FLOOR"}),
    ("heal_over", {"REL_HEAL"}),
    ("no_cap", {"END_CAP", "END_LEVELS", "REPLAY_effects.enduranceCap"}),
    ("pain_kept", {"REL_PAIN", "PAIN_LEVELS", "REPLAY_effects.pain.7"}),
    ("no_beri_pain", {"PAIN_PART", "PAIN_TARGET", "PAIN_LEVELS", "REPLAY_effects.pain.13"}),
    ("pain_lost", {"PAIN_PART", "PAIN_TARGET", "PAIN_ONSET", "PAIN_LEVELS"}),
    ("slow_moodle", {"PAIN_ONSET", "PAIN_FOLLOWS", "PAIN_LEVELS"}),
    ("client_stale", {"PAIN_ONSET", "PAIN_FOLLOWS", "PAIN_LEVELS", "END_LEVELS", "STRESS_LEVELS", "UNHAPPY_LEVELS",
                      "REL_END", "REL_STRESS"}),
    ("no_ease", {"REL_END", "REPLAY_effects.enduranceCap", "REPLAY_drain.target"}),
    ("no_subtract", {"REL_UNHAPPY"}),
    ("no_stress_decay", {"REL_STRESS"}),
    ("no_lapse", {"REL_LAPSE", "REL_UNHAPPY"}),
    ("no_onset", {"ONSET"}),
    ("no_beri", {"BERI_ON"}),
    ("half_take", {"REPLAY_health"}),
]


@pytest.mark.parametrize("flag,grades", FLAGS)
def test_each_defect_moves_its_grade(flag, grades, tmp_path):
    v, out, w, S = run_session(tmp_path, flags=(flag,))
    falsified = {k for k, x in v.items() if x == "falsified"}
    assert grades <= falsified, (flag, bad(v, out))


def test_every_grade_has_a_flag_or_a_pure_failing_case():
    flagged = set().union(*(g for _, g in FLAGS))
    pure = {"OPT", "H1", "RING", "Z", "P0_BASE"}                # their failing cases are the pure tests below
    assert NAMES <= flagged | pure, NAMES - flagged - pure


def test_the_budget_stops_the_session_and_keeps_the_closing_phases(tmp_path):
    v, out, w, S = run_session(tmp_path, budget=150.0)
    assert out["budget_stop"]
    assert {"C", "R"} <= set(out["phase_walls"])


# ---------------------------------------------------------------- the pure helpers and grades
def _ring(n=200, a0=3.0):
    return [{"s": i + 1, "age": a0 + i / 60.0} for i in range(n)]


def _inf(n=200, a0=3.0, **fields):
    rep = [dict({"s": i + 1}, **fields) for i in range(n + 1)]
    return L.InForce(_ring(n, a0), rep)


def _pair(tag, arm, age, **s):
    sd = dict({"online": True, "age": age, "n": 0, "ms": 0.0}, **s)
    return L49.make_pair(tag, arm, sd, age * 1000.0, {"n": 1}, age * 1000.0)


def test_place_progress_reads_across_a_ring_gap():
    rows = [{"s": 1, "age": 3.0, L.F1: 0.9999}, {"s": 3, "age": 3.0 + 2 / 60, L.F1: 0.5}]
    assert L.place_progress(rows, 0.5, 3.0) == 2                   # F6: the drain before row 3, not row 1


def test_place_progress_names_the_drain_that_first_ran_on_it():
    rows = [{"s": 1, "age": 3.0, L.F1: 0.9999}, {"s": 2, "age": 3.0 + 1 / 60, L.F1: 0.9998},
            {"s": 3, "age": 3.0 + 2 / 60, L.F1: 0.5}, {"s": 4, "age": 3.0 + 3 / 60, L.F1: 0.5}]
    assert L.place_progress(rows, 0.5, 3.0 + 1 / 60) == 2
    assert L.place_progress(rows, 0.9, 3.0) is None
    assert L.place_progress(rows, 0.5, None) is None


def test_in_force_reads_the_two_drains_around_a_pair():
    rep = [{"s": 1, "x": 1.0}, {"s": 2, "x": 2.0}, {"s": 3, "x": 3.0}]
    inf = L.InForce(_ring(2), rep)
    assert inf.at(2.0) == (None, None)
    assert inf.both(3.0 + 0.5 / 60, "x") == (1.0, 2.0)
    assert inf.hi(3.0 + 1.5 / 60, "x") == 3.0 and inf.lo(3.0 + 1.5 / 60, "x") == 2.0
    lv, vs = inf.one_level(3.0 + 0.5 / 60, "unhappy", lambda r: 10.0 * r["x"] + 5.0)
    assert lv is None and vs == [15.0, 25.0]                    # Unhappy 0 and 1: no one level
    lv, vs = inf.one_level(3.0 + 0.5 / 60, "unhappy", lambda r: 25.0)
    assert lv == 1


def test_pain_sums_follow_the_jar_modifiers():
    row = {"effects.pain.7": 19.680769, "effects.pain.13": 12.95, "effects.pain.14": 12.95}
    assert L.pain_sum({"effects.pain.7": 19.680769}) == pytest.approx(0.7799999713897705 * 19.680769)
    assert L.pain_mid({"effects.pain.7": 19.680769}) == pytest.approx(15.0, abs=1e-5)
    assert L.pain_mid(row) == pytest.approx(30.0, abs=1e-5)
    assert L.pain_sum(row, injury=3) == pytest.approx(1.2999999523162842 * L.pain_sum(row))


def test_onset_window_is_the_approach_the_timer_and_the_slack():
    lo, hi = L.onset_window(15.0, "s")
    ticks = math.log(3.0) / -math.log(1 - 1 / 500.0)
    assert lo == pytest.approx(0.8 * ticks / 10.0 - 2.0) and hi == pytest.approx(ticks / 10.0 + 12.0 + 5.0)
    assert L.onset_window(15.0, "c")[1] == pytest.approx(ticks / 10.0 + 2.0 + 5.0)
    assert L.onset_window(9.0, "s") is None


def _onset_pairs(t_s, t_c, hz=10.0, fps=60.0, gap=None, n=80):
    """Pairs every 2 s from wall 100 (the ON arm), each side's level 1 from t_s and t_c; the server's ticks and the
    client's frames at hz and fps; gap=(a, b) drops the pairs with a < wall < b (the P1 seed's bus calls)."""
    out = []
    for i in range(n):
        w = 100.0 + 2.0 * i
        if gap and gap[0] < w < gap[1]:
            continue
        out.append(L49.make_pair(f"ON_{i}", "ON", {"online": True, "lvPain": 1 if w >= t_s else 0, "n": hz * w,
                                                   "ms": 1000.0 * w},
                                 w, {"n": fps * w, "ms": 1000.0 * w, "lvPain": 1 if w >= t_c else 0}, w))
    return out


def test_grade_pain_onset():
    v, o, _ = L.grade_pain_onset(_onset_pairs(160.0, 150.0), 99.5, 100.0, 15.0)
    assert v == "as_predicted", o
    assert o["hz"] == pytest.approx(10.0) and o["fps"] == pytest.approx(60.0)
    assert L.grade_pain_onset(_onset_pairs(200.0, 150.0), 99.5, 100.0, 15.0)[0] == "falsified"     # 100 s: late
    assert L.grade_pain_onset(_onset_pairs(120.0, 150.0), 99.5, 100.0, 15.0)[0] == "falsified"     # 20 s: early
    assert L.grade_pain_onset(_onset_pairs(1e9, 150.0), 99.5, 100.0, 15.0)[0] == "falsified"       # never, past hi
    assert L.grade_pain_onset(_onset_pairs(1e9, 145.0, n=25), 99.5, 100.0, 15.0)[0] == "as_predicted"  # c read, s open
    assert L.grade_pain_onset(_onset_pairs(160.0, 150.0), None, 100.0, 15.0)[0] == "unmeasured"


def test_grade_pain_onset_reads_through_a_gap_and_at_the_measured_rates():
    # level 1 at 157 s on the server, read only after a 14 s gap of pairs (the P1 seed's bus calls): the last level-0
    # read (150) and the first level-1 read (166) bracket the change; neither end is outside the window
    v, o, _ = L.grade_pain_onset(_onset_pairs(157.0, 152.0, gap=(151.0, 165.0)), 99.5, 100.0, 15.0)
    assert v == "as_predicted", o
    # the last level-0 read past hi: late, whatever the gap
    assert L.grade_pain_onset(_onset_pairs(178.0, 150.0, gap=(151.0, 165.0)), 99.5, 100.0, 15.0)[0] == "falsified"
    # a server at 8.5 ticks a second: unmeasured
    assert L.grade_pain_onset(_onset_pairs(160.0, 150.0, hz=8.5), 99.5, 100.0, 15.0)[0] == "unmeasured"
    # a client at 5 frames a second: its side unmeasured, the server graded
    v, o, _ = L.grade_pain_onset(_onset_pairs(160.0, 1e9, fps=5.0), 99.5, 100.0, 15.0)
    assert v == "as_predicted" and "unmeasured" in o["sides"]["c"]["why"]
    # the window at the measured rate: at 9.5 Hz the approach alone is about 57.8 s
    lo, hi = L.onset_window(15.0, "s", 9.5, 60.0)
    assert hi == pytest.approx(math.log(3.0) / -math.log(1 - 1 / 500.0) / 9.5 + 120 / 9.5 + 5.0)


def test_grade_part():
    inf = _inf(**{"effects.pain.7": 19.68, "effects.pain.13": 12.95})
    ps = [_pair(f"P1_{i}", "P1", 3.5 + i / 600, part=19.68 - 0.9 * (i % 2)) for i in range(10)]
    reads = {"P1": {"age": 3.6, "parts": {"7": 19.0, "13": 12.5, "14": 0.0}}}
    assert L.grade_part(ps, inf, reads)[0] == "as_predicted"
    low = ps + [_pair("P1_x", "P1", 3.7, part=17.0)]                # under target - 1.53 - 0.01
    assert L.grade_part(low, inf, reads)[0] == "falsified"
    assert L.grade_part(ps, inf, {"P1": {"age": 3.6, "parts": {"13": 11.0}}})[0] == "falsified"
    assert L.grade_part(ps, inf, {"P1": {"age": 3.6, "parts": {"13": 13.0}}})[0] == "falsified"
    assert L.grade_part(ps, _inf(**{"effects.pain.7": 0.0}), reads)[0] == "unmeasured"


def test_grade_pain_target():
    inf = _inf(**{"effects.pain.7": 19.680769})
    ps = [_pair(f"P1_{i}", "P1", 3.5 + i / 600, n=20 * i, ms=2000.0 * i, pain=14.8) for i in range(6)]
    v, o, _ = L.grade_pain_target(ps, "P1", inf)
    assert v == "as_predicted" and o["lo"] == pytest.approx(0.85 * 0.7799999713897705 * (19.680769 - 0.9))
    low = ps[:-1] + [_pair("P1_5", "P1", 3.6, n=100, ms=10000.0, pain=11.0)]
    assert L.grade_pain_target(low, "P1", inf)[0] == "falsified"
    slow = [_pair(f"P1_{i}", "P1", 3.5 + i / 600, n=12 * i, ms=2000.0 * i, pain=14.8) for i in range(6)]
    assert L.grade_pain_target(slow, "P1", inf)[0] == "unmeasured"                                # 6 ticks a second
    assert L.grade_pain_target([], "P1", inf)[0] == "unmeasured"


def test_grade_end_cap_and_the_floors():
    inf = _inf(**{"effects.enduranceCap": 0.355, "effects.stressFloor": 0.3, "effects.unhappyFloor": 25.0})
    ok = [_pair(f"P1_{i}", "P1", 3.5 + i / 600, endurance=0.36, stress=0.2985, unhappy=25.2) for i in range(5)]
    assert L.grade_end_cap(ok, inf)[0] == "as_predicted"
    assert L.grade_end_cap(ok + [_pair("x", "P1", 3.6, endurance=0.40)], inf)[0] == "falsified"
    assert L.grade_stress_floor(ok, inf)[0] == "as_predicted"
    assert L.grade_stress_floor(ok + [_pair("x", "P1", 3.6, stress=0.29)], inf)[0] == "falsified"
    rows = [{"s": r["s"], "age": r["age"], "moodLast.u": 25.0, "effects.unhappyFloor": 25.0} for r in _ring()]
    spans = {"P1": (3.4, 3.7)}
    assert L.grade_unhappy_floor(ok, inf, rows, spans)[0] == "as_predicted"
    assert L.grade_unhappy_floor(ok + [_pair("x", "P1", 3.6, unhappy=24.0)], inf, rows, spans)[0] == "falsified"
    rows_u = [dict(r, **{"moodLast.u": 0.0}) for r in rows]                     # the writer's target lacks the floor
    assert L.grade_unhappy_floor(ok, inf, rows_u, spans)[0] == "falsified"
    assert L.grade_unhappy_floor(ok, inf, rows, {})[0] == "unmeasured"
    assert L.grade_end_cap([], inf)[0] == "unmeasured"
    assert L.grade_stress_floor([], inf)[0] == "unmeasured"


def test_grade_opt():
    row = {"s": 1, L.OPT_PACE: 3, L.OPT_COMBINE: 2, L.OPT_DAYMIN: 90, L.SB_SEVERITY: 1.0, L.POLLED_SEVERITY: 1}
    prof = L.PROFILES["x49-accept"]
    assert L.grade_opt([row], prof)[0] == "as_predicted"
    assert L.grade_opt([dict(row, **{L.OPT_PACE: 2})], prof)[0] == "falsified"
    assert L.grade_opt([dict(row, **{L.SB_SEVERITY: None})], prof)[0] == "falsified"
    assert L.grade_opt([], prof)[0] == "unmeasured"


def test_grade_z_h1_ring_and_base():
    assert L.grade_z([], False, {})[0] == "as_predicted"
    assert L.grade_z(["NR_Server_Effects.lua:12 attempted index"], False, {})[0] == "falsified"
    assert L.grade_z([], False, {"S.server": "boom"})[0] == "falsified"
    assert L.grade_z([], None, {})[0] == "unmeasured"
    h1 = {"ok": True, "missing": {"drain.frac.1": "nil"}}
    assert L48.grade_h1(h1, {"ok": True}, L.H1_NIL_OK)[0] == "as_predicted"
    assert L48.grade_h1({"ok": True, "missing": {"effects.pain.7": "nil"}}, {"ok": True}, L.H1_NIL_OK)[0] == "falsified"
    assert L.G.grade_ring([{"file": "a.json", "reply": {"errors": 1}}])[0] == "falsified"
    assert L.G.grade_ring([])[0] == "unmeasured"
    pair = _pair("S", "S", 3.0, pain=0.0, stress=0.0, nicotine=0.0, unhappy=0.0, endurance=1.0)
    assert L49.grade_base(pair, {"parts": [{"index": 7, "additionalPain": 0.0}]})[0] == "as_predicted"
    assert L49.grade_base(pair, {"parts": [{"index": 7, "additionalPain": 5.0}]})[0] == "falsified"


def test_grade_lapse():
    rows = [{"s": 1, "age": 3.0, "drain.mask": 5}, {"s": 2, "age": 3.0 + 1 / 60, "drain.mask": 5},
            {"s": 3, "age": 3.0 + 2 / 60, "drain.mask": 4, "drain.recovering": 1}]
    a = 3.0 + 0.5 / 60
    assert L.grade_lapse(rows, a)[0] == "as_predicted"
    assert L.grade_lapse(rows[:2] + [{"s": 3, "age": 3.1, "drain.mask": 4}], a)[0] == "falsified"   # 5.5 minutes
    assert L.grade_lapse(rows[:2], a)[0] == "unmeasured"
    assert L.grade_lapse(rows[:2] + [{"s": 3, "age": 3.2, "drain.mask": 5}], a)[0] == "falsified"   # never
    assert L.grade_lapse(rows, None)[0] == "unmeasured"


def _rel_pairs(n=30, a_l=4.0, part0=19.0, rate=0.9, stress0=0.55, srate=0.0018, e0=0.125, climb=0.0066, gm=0.5,
               lv_end=None, lv_stress=None, unhappy_lv=0):
    out = []
    for i in range(n):
        age = a_l + 1.5 / 60 + i * gm / 60
        t = 1.5 + i * gm                                                         # game minutes since the lapse row
        e = min(0.73, e0 + climb * t)
        s = stress0 - srate * t
        le = L49.level_of("endurance", e) if lv_end is None else lv_end
        ls = L49.level_of("stress", s) if lv_stress is None else lv_stress
        arm = "L1" if i < n // 3 else "L2"
        side = {"endurance": e, "lvEnd": le, "stress": s, "lvStress": ls, "lvUnhappy": unhappy_lv}
        sd = dict({"online": True, "age": age, "part": max(0.0, part0 - rate * i * gm)}, **side)
        out.append(L49.make_pair(f"{arm}_{i}", arm, sd, i * 2.0, dict(side), i * 2.0))
    return out


def test_grade_rel_pain():
    assert L.grade_rel_pain(_rel_pairs(gm=1.0), 4.0)[0] == "as_predicted"
    assert L.grade_rel_pain(_rel_pairs(gm=1.0, rate=0.8), 4.0)[0] == "falsified"
    assert L.grade_rel_pain(_rel_pairs(gm=0.5), 4.0)[0] == "as_predicted"          # a shortened arm: its own end
    flat = _rel_pairs(gm=1.0)
    for p in flat[-8:]:
        p["s"]["part"] = flat[-9]["s"]["part"] if flat[-9]["s"]["part"] > 0 else 3.0
    flat = _rel_pairs(gm=0.5)
    for p in flat[-10:]:
        p["s"]["part"] = flat[-11]["s"]["part"]                                       # the decay stops: set again
    assert L.grade_rel_pain(flat, 4.0)[0] == "falsified"
    rose = _rel_pairs(gm=1.0)
    rose[12]["s"]["part"] = 19.6
    assert L.grade_rel_pain(rose, 4.0)[0] == "falsified"
    assert L.grade_rel_pain(_rel_pairs(gm=1.0, part0=1.0), 4.0)[0] == "unmeasured"
    assert L.grade_rel_pain(_rel_pairs(gm=1.0), None)[0] == "unmeasured"


def test_grade_rel_end():
    inf = _inf(n=400, a0=3.5, **{"effects.enduranceCap": 0.7295})
    ps = _rel_pairs(n=60, gm=1.5)
    assert L.grade_rel_end(ps, inf, 4.0, 0.125)[0] == "as_predicted"
    assert L.grade_rel_end(ps, _inf(n=400, a0=3.5, **{"effects.enduranceCap": 0.125}), 4.0, 0.125)[0] == "falsified"
    pulled = _rel_pairs(n=60, gm=1.5)
    pulled[30]["s"]["endurance"] = 0.1
    assert L.grade_rel_end(pulled, inf, 4.0, 0.125)[0] == "falsified"
    stuck = _rel_pairs(n=60, gm=1.5, lv_end=3)                                   # a moodle left at P2's level
    assert L.grade_rel_end(stuck, inf, 4.0, 0.125)[0] == "falsified"
    assert L.grade_rel_end(ps, inf, None, 0.125)[0] == "unmeasured"


def test_grade_rel_stress():
    ps = _rel_pairs(n=60, gm=1.5)
    assert L.grade_rel_stress(ps, 4.0, 0.55)[0] == "as_predicted"
    assert L.grade_rel_stress(_rel_pairs(n=60, gm=1.5, srate=0.0), 4.0, 0.55)[0] == "falsified"
    raised = _rel_pairs(n=60, gm=1.5)
    raised[20]["s"]["stress"] = 0.6
    assert L.grade_rel_stress(raised, 4.0, 0.55)[0] == "falsified"
    assert L.grade_rel_stress(_rel_pairs(n=60, gm=1.5, lv_stress=2), 4.0, 0.55)[0] == "falsified"
    assert L.grade_rel_stress(ps, 4.0, None)[0] == "unmeasured"


def test_grade_rel_unhappy():
    rows = [{"s": 1, "age": 3.0, "moodLast.u": 50.0, "UNHAPPINESS": 51.4},
            {"s": 2, "age": 3.0 + 1 / 60, "moodLast.u": 50.0, "UNHAPPINESS": 51.5},
            {"s": 3, "age": 3.0 + 2 / 60, "moodLast.u": 0.03, "UNHAPPINESS": 1.6}]
    ps = _rel_pairs(n=15, a_l=3.0)
    a = 3.0 + 1.5 / 60
    assert L.grade_rel_unhappy(rows, ps, a)[0] == "as_predicted"
    kept = [dict(r) for r in rows]
    kept[2]["UNHAPPINESS"] = 51.6                                             # the floor left, the stat kept
    assert L.grade_rel_unhappy(kept, ps, a)[0] == "falsified"
    assert L.grade_rel_unhappy(rows, _rel_pairs(n=15, a_l=3.0, unhappy_lv=2), a)[0] == "falsified"
    held = [dict(r, **{"moodLast.u": 50.0}) for r in rows] + [{"s": 4, "age": 3.2, "moodLast.u": 50.0}]
    assert L.grade_rel_unhappy(held, ps, a)[0] == "falsified"
    assert L.grade_rel_unhappy(rows[:2], ps, a)[0] == "unmeasured"


# ---------------------------------------------------------------- the pre-boot checks, the prerun and the driver
def test_preboot_on_the_repository():
    pre, ok = L.preboot("x494", L.SESSIONS["x494"]["driver"])
    if not pre["no_prior_artifact"]:
        pytest.skip("the session's artifact is committed: preboot refuses it by design")
    if not os.path.isfile(os.path.join(REPO, L48.FIXTURE_PLAYERS_DB)):
        pytest.skip("the default fixture cache is not provisioned on this machine")
    assert ok, {k: v for k, v in pre.items() if v is not True}


def test_preboot_refuses_a_wrong_file_a_stale_prerun_and_a_prior_artifact(tmp_path):
    assert L.preboot("x494", "x491_levers.py")[1] is False
    assert L.preboot("x495", "x495_x.py")[1] is False
    stale = L.preboot("x494", "x494_accept.py", compute=lambda keys: {"x494": {"x": 1}})
    assert stale[1] is False and stale[0]["prerun_current"] is False
    fake = tmp_path / "repo"
    (fake / "testing" / "artifacts" / "x494-20261021-000000").mkdir(parents=True)
    pre, ok = L.preboot("x494", "x494_accept.py", repo=str(fake), compute=lambda keys: {"x494": {}})
    assert ok is False and pre["no_prior_artifact"] is False


def test_profile_checks_fail_each_key():
    import tomllib
    name = "x49-accept"
    text = open(os.path.join(REPO, "testing", "profiles", name + ".toml"), encoding="utf-8").read()
    doc = tomllib.loads(text)
    assert all(L.profile_doc_checks(name, doc, text).values())
    m = doc["mods"]
    sb, srv, nr = doc["sandbox"], doc["server"], doc["sandbox"]["NR"]
    muts = [("fixture", "two"), ("clients", ["admin", "bob"]), ("server", dict(srv, SleepAllowed=True)),
            ("mods", m[:2]), ("mods", [m[0], dict(m[1], path="mod/NutritionRevamp"), m[2]]),
            ("mods", [m[0], m[1], dict(m[2], path="x")]),
            ("sandbox", dict(sb, Nutrition=True)), ("sandbox", dict(sb, DayLength=1)),
            ("sandbox", dict(sb, NR=dict(nr, Severity=2.0))), ("sandbox", dict(sb, NR=dict(nr, Mode=2))),
            ("verify", doc["verify"][:2]), ("server", dict(srv, timeout=120))]
    for k, v in muts:
        d = dict(doc, **{k: v})
        assert not all(L.profile_doc_checks(name, d, text).values()), k
    assert not L.profile_doc_checks(name, doc, text[2:])["header_names_file"]


@need_staged
def test_the_staged_upload_copy_is_mod_head_at_1_0_0():
    # a pre-run guard on the live release/ copy while the session is unrun; once x494 has run, mod/ and the upload
    # copy move on and the gate is proved on a fresh stage of the pinned commit instead (x48b's precedent)
    arts = os.listdir(os.path.join(REPO, "testing", "artifacts"))
    if not any(d.startswith("x494-") for d in arts):
        mg = L.staged_gate()
        assert mg["ok"], mg
        assert mg["staged_version"] == L.STAGED_VERSION and mg["commit"] == L.STAGED_FROM
        assert L.STAGED_FROM.startswith(L.mod_head()) or L.mod_head().startswith(L.STAGED_FROM)
        return
    import io
    import subprocess
    import tarfile
    import tempfile
    import release_pack as RP
    with tempfile.TemporaryDirectory(dir=os.path.join(REPO, "release")) as d:
        arch = subprocess.run(["git", "archive", "--format=tar", L.STAGED_FROM, L.MOD_DIR], cwd=REPO,
                              capture_output=True, check=True)
        with tarfile.open(fileobj=io.BytesIO(arch.stdout)) as tf:
            tf.extractall(d, filter="data")
        out = os.path.join(d, "stage")
        RP.main(["stage", os.path.join(d, *L.MOD_DIR.split("/")), "--out", out])
        root = os.path.relpath(os.path.join(out, "NutritionRevamp"), REPO).replace(os.sep, "/")
        mg = L.G.staged_gate(repo=REPO, commit=L.STAGED_FROM, stage_root=root,
                             stage_mod=root + "/Contents/mods/NutritionRevamp")
        assert mg["ok"], mg


def test_the_harness_and_probe_markers_and_the_fixture():
    assert L49.markers_ok(L.HARNESS_FILES, L.HARNESS_MARKERS)[1]
    assert L49.markers_ok({p: p for p in L.PROBE_MARKERS}, L.PROBE_MARKERS)[1]
    if not os.path.isfile(os.path.join(REPO, L48.FIXTURE_PLAYERS_DB)):
        pytest.skip("the default fixture cache is not provisioned on this machine")
    assert L48.fixture_fresh()["fresh"]


def test_the_prerun_is_the_head_replay_and_reads_as_documented():
    pr = L48.prerun_current("x494", REPO, PR.compute, committed=L.load_prerun())
    assert pr["ok"], pr.get("diff")
    p = L.load_prerun()["x494"]
    lv = {k: p["arms"][k]["levels"] for k in p["arms"]}
    assert lv["P1"] == {"endurance": 2, "pain": 1, "stress": 1, "unhappy": 1}
    assert lv["B"] == {"endurance": 2, "pain": 2, "stress": 1, "unhappy": 1}
    assert lv["P2"] == {"endurance": 3, "pain": 2, "stress": 2, "unhappy": 2}
    assert lv["L2"]["pain"] == 1 and lv["L2"]["stress"] == 0 and lv["L2"]["unhappy"] == 0
    assert p["lapse"]["lag_m"] == 0 and p["lapse"]["mask"] == 4 and p["lapse"]["recovering"] == 1
    assert p["lapse"]["cap_after"] > 0.72 and p["lapse"]["u_after"] < 0.1
    assert p["arms"]["L2"]["effects.pain.7"] == 0.0 and p["arms"]["L2"]["effects.pain.13"] == 12.95
    assert p["beri_lag_m"] <= 2


def test_the_snack_opens_a_meal_spell_and_the_floor_seeds_are_the_knots():
    import re
    src = open(os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Kernel_Drain.lua"),
               encoding="utf-8").read()
    suspend = float(re.search(r"K\.drain\.SUSPEND_M = ([0-9.]+)", src).group(1))
    assert L.SNACK_M >= suspend                               # a real snack's pool: the spell opens before the clearing
    assert L.load_prerun()["x494"]["lapse"]["lag_m"] == 0          # since 6ee7c8d1 (driver review concern 1)
    assert L.load_prerun()["x494"]["floors_seeded"] == {"P1": [0.3, 25.0], "P2": [0.55, 50.0]}


def test_the_driver_names_its_session_refuses_arguments_and_predicts_every_grade():
    src = open(os.path.join(EXP, "x494_accept.py"), encoding="utf-8").read()
    assert 'KEY = "x494"' in src and 'PREFIX = "x494"' in src and 'PROFILE = "x49-accept"' in src
    i_ref, i_main = src.index("L.parse_argv(sys.argv[1:]"), src.index("L.main(KEY")
    assert i_ref < i_main and "sys.exit(refusal)" in src[i_ref:i_main]
    assert "takes no arguments" in L.parse_argv(["--fast"], "x494_accept.py")
    assert L.parse_argv([], "x494_accept.py") is None
    import importlib
    D = importlib.import_module("x494_accept")
    assert set(D.PRED) == NAMES and all(D.PRED.values())
    assert D.BUDGET_S <= 540.0


def test_the_ring_is_within_the_harness_cap_and_carries_every_replay_field():
    assert len(L.RING) <= 32 and len(set(L.RING)) == len(L.RING)
    assert all(f in L.RING or f == "health" for f in L.REPLAY_TOL)


def test_grade_rel_end_skips_a_sample_at_an_edge_and_reads_a_short_arm_unmeasured():
    inf = _inf(n=400, a0=3.5, **{"effects.enduranceCap": 0.7295})

    def crossing(stale_level):
        ps = _rel_pairs(n=60, gm=1.5)
        for p in ps[:55]:
            for side in ("s", "c"):
                p[side]["endurance"] = min(p[side]["endurance"], 0.47)
                p[side]["lvEnd"] = L49.level_of("endurance", p[side]["endurance"])
        # the five L2 pairs cross 0.5; at 0.5005 the moodle still reads the level of the tick before (F4)
        for i, e in zip(range(55, 60), (0.477, 0.494, 0.5005, 0.529, 0.547)):
            for side in ("s", "c"):
                ps[i][side]["endurance"] = e
                ps[i][side]["lvEnd"] = stale_level if e == 0.5005 else L49.level_of("endurance", e)
        return ps
    v, o, _ = L.grade_rel_end(crossing(2), inf, 4.0, 0.125)
    assert v == "as_predicted", o                                               # the stale sample skipped
    assert o["graded_a_side"] == {"s": 4, "c": 4}
    off = crossing(2)
    off[58]["s"]["lvEnd"] = 2                                                    # a stale level away from the edge
    assert L.grade_rel_end(off, inf, 4.0, 0.125)[0] == "falsified"
    assert L.grade_rel_end(crossing(2), inf, 4.0, 0.125, short=True)[0] == "unmeasured"
    lone = crossing(2)
    for i in range(55, 60):
        for side in ("s", "c"):
            lone[i][side]["endurance"] = 0.5005                                  # every sample at the edge
    assert L.grade_rel_end(lone, inf, 4.0, 0.125)[0] == "unmeasured"


def test_grade_rel_stress_skips_a_prediction_at_a_threshold_and_a_short_arm():
    # STRESS sits 0.003 under its floor at the lapse (the write's oscillation), so near 0.5 the predicted level (off
    # the floor 0.55) and the real one part: those pairs are skipped (F7), and the pair clear of the edge is graded
    ps = _rel_pairs(n=24, gm=1.5, a_l=4.0, stress0=0.547)
    v, o, _ = L.grade_rel_stress(ps, 4.0, 0.55)
    assert v == "as_predicted", o
    assert len(o["levels"]) == 2                                                 # one pair of five, both sides
    assert L.grade_rel_stress(_rel_pairs(n=60, gm=1.5), 4.0, 0.55, short=True)[0] == "unmeasured"


def test_a_shortened_arm_reads_its_timed_grades_unmeasured_never_falsified(tmp_path):
    # a budget that leaves L2 about 10 s: the grades timed on the full arm read unmeasured
    v, out, w, S = run_session(tmp_path, budget=333.0)                 # L2 starts at about 298 s in the fake
    l2 = S.arm_rec("L2")
    assert l2 and l2["secs_given"] < l2["secs_asked"] - 0.5, l2.get("secs_given")
    assert "L2" in out["arms_short"]
    for name in ("PAIN_LEVELS", "REL_END", "REL_STRESS"):
        assert v[name] == "unmeasured", (name, out["verdicts"][name]["observed"])
    assert "falsified" not in v.values(), bad(v, out)


class _SlowClient:
    def __init__(self, clock):
        self.clock, self.alive, self.username = clock, True, "admin"

    def quit(self, timeout=60):
        self.clock[0] += timeout                                   # a quit that waits its whole timeout
        self.alive = False
        return None


class _SlowServer:
    def __init__(self, clock):
        self.clock, self.alive, self.errors = clock, True, []

    def stop(self, timeout=120):
        self.clock[0] += timeout
        self.alive = False
        return None


def test_the_bounded_teardown_keeps_the_call_under_600_s():
    import x494_accept as D
    clock = [0.0]
    out = T48.fresh_out()
    xs = X.Xs(out, node=lambda side: side, clients={}, budget_s=D.BUDGET_S, clock=lambda: clock[0],
              sleep=lambda dt: None)
    clock[0] = D.BUDGET_S + 20.0                                   # the phases at the budget, C and R after
    xs.server = _SlowServer(clock)
    tl = type("TL", (), {"items": [], "mark": lambda self, *a, **k: None})()
    xs.tl = tl
    xs.finish(L.bounded_teardown, lambda server, every: None, [_SlowClient(clock)])
    assert out["wall_seconds"] <= D.BUDGET_S + 20 + L.TEARDOWN_QUIT_S + L.TEARDOWN_STOP_S + 10
    assert out["wall_seconds"] < 600.0
