"""x35_exercise_lib and x35_grade (Plan 11f Task 6r): rows 9 and 10 under the C-17 activity billing. The chain's calendar
and ring; the replay's movement and autodrop events; the bout on a fake server and clock (a set followed past its
window until the flag clears, the rest at speed 1 with paired reads, the walk leg; ruling T7-2); the in-driver billing
reading; and the grade's row 9 and walk leg on a synthetic live ring made by the mod's own server replay from a known
engine rate, exercise flag and movement (the ring's own phase: ring row s reads the state drain s - 1 left), with the
grade shown to bite on a tail row, a wrong pool and a capless walk. Pure Python on the lupa host: no game."""
import json
import math
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))                          # testing/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))
sys.path.insert(0, os.path.join(REPO, "tools"))

import replay_live as RL   # noqa: E402
import x35_exercise_lib as L   # noqa: E402
import x35_grade as G   # noqa: E402
from pzt.session import Timeline   # noqa: E402


def K():
    return L._kh_static().K


# --- the calendar and the ring -------------------------------------------------------------------------------------

def test_the_chain_calendar_and_the_ring():
    kinds = {}
    for age, kind, label in L.SCHEDULE:
        kinds.setdefault(kind, []).append((label, age))
    assert [x[0] for x in kinds["bout"]] == ["B0", "B1", "B2", "B3", "B4", "B5"]
    assert kinds["bout"][0][1] == L.at(0, 15.0) == 8.0 and kinds["bout"][-1][1] == L.at(5, 15.0) == 128.0
    assert L.END_CHAIN == L.at(5, 17.5) == 130.5
    assert kinds["maint"][-1] == ("D5_13", L.at(5, 13.0))
    assert len(L.RING_RECORD) + len(L.RING_GLOBALS) == 30 and L.EPOC in L.RING_RECORD
    ages = [x[0] for x in L.SCHEDULE]
    assert ages == sorted(ages)
    assert G.LAST_DAY == 5 and L.at(G.LAST_DAY, 15.0) == 128.0


# --- the replay's events -------------------------------------------------------------------------------------------

def test_moving_events_change_only_skip_offline_and_never_name_the_rate():
    rows = [{"s": 1, "age": 1.0, "moving": False}, {"s": 2, "age": 1.02, "moving": True},
            {"s": 3, "age": 1.03, "moving": True}, {"s": 4, "age": 1.05, "on": False, "moving": False},
            {"s": 5, "age": 1.07}, {"s": 6, "age": 1.08, "moving": False}]
    ev = L.ring_moving_events(rows)
    assert [(e["s"], e["moving"]) for e in ev] == [(2, True), (6, False)]
    assert all(not any(k in e for k in RL.RING_ACTIVITY_KEYS) for e in ev)


def test_autodrop_events_use_the_tool_kind():
    ev = L.autodrop_events([{"s": 1, "age": 1.0, L.AUTODROP: 0.0}, {"s": 2, "age": 1.02, L.AUTODROP: 0.1}])
    assert ev == [{"s": 2, "kind": "autodrop", "g": 200.0, "label": "autodrop", "autoDrop": 0.1, "age": 1.02}]


# --- a synthetic live ring: the mod's own server replay on a known engine rate, flag and movement --------------------

TAU_RISE_M, TAU_FALL_M = 0.558 * 60, 1.36 * 60        # the engine's measured lag at DayLength 1 (the C-17 report)


def engine(n, sets, walks, idle=1.5, target=6.0, walk_target=3.1):
    """Per minute 0..n-1: (raw rate, exercise flag, moving), the rate a first-order lag toward the set's target while a
    set runs, toward the walk target while walking (falling from a set's rate) and toward idle otherwise."""
    out, r = [], idle
    for m in range(n):
        ex = any(a <= m < b for a, b in sets)
        mv = any(a <= m < b for a, b in walks)
        goal, tau = (target, TAU_RISE_M) if ex else ((walk_target, TAU_FALL_M) if mv else (idle, TAU_FALL_M))
        if goal > r:
            tau = TAU_RISE_M
        r = r + (goal - r) * (1 - math.exp(-1.0 / tau))
        out.append((r, ex, mv))
    return out


def start_record():
    with open(os.path.join(REPO, "testing", "artifacts", "x281-20261011-033356", "start.json"), encoding="utf-8") as fh:
        return json.load(fh)


def synth(sets, walks, n=420, acute=True):
    """(ring, start): ring rows labelled as the harness samples (row s reads the state drain s - 1 left), each carrying
    the raw rate, exe and moving in effect for its own drain."""
    start = start_record()
    t0 = start["rec"]["satiety"]["t"]
    eng = engine(n, sets, walks)
    clock = [{"s": i + 1, "age": t0 + (i + 1) / 60.0, "dtM": 1.0, "on": True, "ev": i + 1, "drained": i}
             for i in range(n)]
    ev = []
    for i, (raw, ex, mv) in enumerate(eng):
        ev.append({"s": i + 1, "kind": "activity", "raw": raw, "exercising": ex, "moving": mv})

    def run():
        return RL.replay_live(clock, ev, start, paths=list(L.RING_RECORD), sleep_allowed=False, ring_activity=False)[0]
    out = run() if acute else G.no_acute(run)
    by = {r["s"]: r for r in out}
    ring = []
    for i, c in enumerate(clock[1:], 1):
        r = dict(by[c["s"]])
        r.update(c)
        raw, ex, mv = eng[i]
        r.update({"rate": raw, "exe": ex, "moving": mv})
        ring.append(r)
    return ring, start


class FakeSess:
    def __init__(self, ring, start, stops):
        self.pre, self.ring, self.start = "x35s", ring, start
        self.ring_by = {r["s"]: r for r in ring}
        self.doc = {"stops": stops, "pairs": []}
        self.events = []
        self.hold = set()
        self.rows = [dict(r) for r in ring]
        self.rep_by = {r["s"]: r for r in self.rows}
        self.na_by = {}

    def bout(self, label):
        return next((s for s in self.doc["stops"] if s.get("label") == label), None)


SET = (30, 100)            # minutes: a 70-minute set (past a 60-minute window, as x29's B0 overran)


def row9_sess(mutate=None):
    ring, start = synth([SET], [])
    na, _ = synth([SET], [], acute=False)
    if mutate:
        mutate(ring)
    S = FakeSess(ring, start, [{"kind": "bout", "label": "B0", "age0": ring[25]["age"], "age1": ring[-1]["age"],
                                "set_end_age": ring[SET[1] - 1]["age"],
                                "sets": [{"label": "B0_s0", "clear_age": ring[SET[1] - 1]["age"] + 0.2 / 60}]}])
    S.na_by = {r["s"]: r for r in na}
    return S


def test_the_grade_reads_row_9_off_the_mods_own_billing():
    k = K()
    r9 = G.row9(row9_sess())
    b = r9["billed_6_from_first"]
    assert b["ok"] and b["billed_next"] == 6.0 and b["not_fitness"] == 0 and b["flagged_drains"] == SET[1] - SET[0]
    assert r9["exe_end"]["ok"] and r9["exe_end"]["rows_unflag_minus_turn"] == 0
    assert r9["exe_end"]["ok_poll"] and r9["exe_end"]["rows_unflag_minus_poll"] == -1    # ring index j holds minute j + 1
    ia = r9["idle_after"]
    assert ia["ok"] and ia["clear_minute_met"] == 1.3 and ia["tail_rows"] == 0 and ia["tail_kcal"] == 0.0
    ep = r9["epoc"]
    assert ep["ok"] and ep["step_max_rel"] < 1e-9 and abs(ep["set_ex_kcal"] - 4.7 * 80 * 70 / 60) < 1e-6
    assert abs(ep["released_over_target"] - 1) < 0.01
    sv = r9["S"]
    assert sv["rise"]["ok"] and sv["rise"]["rows"] == SET[1] - SET[0] and sv["decay"]["ok"]
    assert abs(sv["rise"]["S_max"] - 0.5 * (1 - 0.5 ** (70 / 30.0))) < 1e-9
    f = r9["factor"]
    assert f["ok"] and f["graded"] > 100 and f["max_rel"] < 1e-9 and f["mean_ratio_over_set"] < 1.0
    assert float(k.energy.EPOC_F) == ep["EPOC_F"]


def test_the_row_9_grade_bites():
    def tail(ring):
        ring[SET[1] + 5]["body.met"] = 1.9
        ring[SET[1] + 6]["body.met"] = 1.9                               # one tail row is allowed, two are not
    assert G.row9(row9_sess(tail))["idle_after"]["ok"] is False

    def pool(ring):
        for r in ring[SET[1] + 2:]:
            if r.get(L.EPOC) is not None:
                r[L.EPOC] = r[L.EPOC] * 1.5
    assert G.row9(row9_sess(pool))["epoc"]["step_max_rel"] > 0.1

    def late(ring):
        ring[SET[0]]["body.met"] = 1.3                                   # the first flagged drain's bill (row f + 1)
    assert G.row9(row9_sess(late))["billed_6_from_first"]["ok"] is False


def walk_sess(capped=True):
    ring, start = synth([(30, 90)], [(91, 140)], n=200)
    if not capped:
        for r in ring[95:120]:
            r["body.met"] = 4.0
    w = {"age0": ring[90]["age"], "age1": ring[139]["age"], "walks": [1, 2], "polls": [], "moving_polls": 20}
    return FakeSess(ring, start, [{"kind": "bout", "label": "B5", "age0": ring[25]["age"], "age1": ring[-1]["age"],
                                   "walk": w, "sets": []}])


def test_the_walk_leg_reads_the_cap_and_bites():
    w = G.walk_leg(walk_sess())
    assert w["ok"] and w["moving_falling_rows"] > 20 and max(float(x) for x in w["met_hist_moving_falling"]) <= 3.8
    assert G.walk_leg(walk_sess(capped=False))["ok"] is False


def test_the_ring_activity_and_the_moving_events_reproduce_the_billing():
    ring, start = synth([(30, 90)], [(91, 140)], n=200)
    mv = [e for e in L.ring_moving_events(ring) if e["s"] > ring[0]["s"]]
    out, be = RL.replay_live(ring, mv, start, paths=list(L.RING_RECORD), sleep_allowed=False)
    assert be.ring_activity                                            # the tool took the rate and the flag itself
    by = {r["s"]: r for r in out}
    for r in ring[2:]:
        for p in ("body.met", "satiety.S", "satiety.L", L.EPOC, "body.exKcalDay"):
            assert by[r["s"]].get(p) == r.get(p), (r["s"], p, by[r["s"]].get(p), r.get(p))


def test_the_in_driver_billing_reading():
    ring, _ = synth([SET], [])
    x = L.billing_reading(ring, ring[20]["age"], ring[-1]["age"])
    assert x["flagged"] == SET[1] - SET[0] and x["on_flag_billed_fitness"] == x["on_flag_rows"] == x["flagged"]
    assert x["tail_rows"] == 0 and x["tail_kcal"] == 0.0 and x["epoc_max"] > 0 and x["next_two_mets"][1] == 1.3
    ring[SET[1] + 3]["body.met"] = 2.0
    assert L.billing_reading(ring, ring[20]["age"], ring[-1]["age"])["tail_rows"] == 1


# --- the bout on a fake server and clock -----------------------------------------------------------------------------

class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now

    def sleep(self, s):
        self.now += max(s, 0.01)


class FakeServer:
    """Each answer advances the world one game minute. exercise.do starts a set that runs SET_M game minutes whatever
    it asked; witness.chain answers the exercise, the rate and the movement; stats.all answers either side."""
    SET_M = 80

    def __init__(self, clock, age=8.0):
        self.clock, self.age = clock, age
        self.set_end = None
        self.ex = 100.0
        self.cmds = []
        self.walking_until = None

    def answer(self, side, cmd, args):
        self.clock.now += 1.0
        self.age += 1.0 / 60
        self.cmds.append((side, cmd, args))
        on = self.set_end is not None and self.age < self.set_end
        if on:
            self.ex += 0.0627
        if cmd == "exercise.do":
            self.set_end = self.age + self.SET_M / 60.0
            return {"ok": True, "queued": True}
        if cmd == "witness.chain":
            ch = args.split()[1]
            if ch == L.EXE_CHAIN:
                return {"ok": True, "value": "zombie.Fitness$FitnessExercise@1" if on else "nil"}
            if ch == L.MOVE_CHAIN:
                return {"ok": True, "value": self.walking_until is not None and self.age < self.walking_until}
            return {"ok": True, "value": 4.0 if on else 3.0}
        if cmd == "player.walk":
            self.walking_until = self.age + 8.0 / 60
            return {"queued": True, "clientMoving": True}
        if cmd == "player.stop":
            self.walking_until = None
            return {"cleared": True}
        if cmd == "lua.read":
            return {"ok": True, "values": {p: (self.ex if p.endswith("exKcalDay") else 1.0) for p in args.split()[1:]}}
        if cmd == "stats.all":
            return {"worldAge": self.age, "stats": {"HUNGER": 0.2, "THIRST": 0.1}}
        if cmd == "time.snapshot":
            return {"worldAge": self.age, "hour": 15, "minutes": 0, "mult": 1}
        return {"ok": True}


def fake_session(tmp_path, fake, walk_bouts=(), rest_one=None):
    S = object.__new__(L.Session)
    S.out = {"phase_walls": {}, "phase_errors": {}, "notes": [], "phases": {"X": {}}, "deviations": [], "steps": [],
             "verdicts": {}, "readings": {}}
    S.tl, S.t0, S.cur = Timeline(), fake.clock.now, "X"
    S.path = str(tmp_path / "doc.json")
    S.run_dir = str(tmp_path)
    S.server, S.clients, S.started = None, {}, []
    S.stops, S.marks, S.speeds, S.eats, S.drinks, S.pairs = [], [], [], [], [], []
    S.budget_s = 1e9
    S.bout_ex = "burpees"
    S.walk_bouts, S.rest_one = tuple(walk_bouts), dict(rest_one or {})
    S.last_bout = 0.0

    def step(name, side, cmd, args="", timeout=30, log=True):
        w = S.wall()
        return {"step": name, "side": side, "cmd": cmd, "args": args, "phase": S.cur, "wall_before": w,
                "wall_after": w + 0.2, "took": 0.2, "ack": fake.answer(side, cmd, args)}
    S.step = step
    S.check = lambda: None
    S.one = lambda tag="one": {}
    S.fast = lambda tag="fast": {}
    S.rcon = lambda cmd, tag: {"ok": True}
    return S


def patch_clock(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(L, "time", types.SimpleNamespace(time=clock.time, sleep=clock.sleep))
    monkeypatch.setattr(L, "POLL_S", 0.0)
    return clock


def test_a_set_is_followed_past_its_window_then_the_rest_runs_at_speed_one(tmp_path, monkeypatch):
    fake = FakeServer(patch_clock(monkeypatch))
    S = fake_session(tmp_path, fake, rest_one={"B0": 180.0})
    st = S.bout("B0", 8.0, 13.0)
    assert len(st["sets"]) == 1 and st["sets"][0]["ended"] is True
    clear = st["sets"][0]["clear_age"]
    assert clear >= fake.set_end - 1e-9 and clear > st["age0"] + L.BOUT_MIN / 60.0     # followed past the window
    assert st["set_end_age"] == clear and st["rest_m"] == 180.0
    assert abs(st["rest_end_age"] - (clear + 3.0)) < 1e-9 and st["age1"] >= st["rest_end_age"] - 1e-9
    assert [p["tag"] for p in S.pairs] == ["B0_p0", "B0_p15", "B0_p30", "B0_p60", "B0_p120", "B0_p180"]
    assert all(p["wall_gap"] is not None and p["client"]["HUNGER"] == 0.2 for p in S.pairs)
    assert st["bout_kcal"] > 0 and "walk" not in st


def test_the_rest_stops_before_the_next_stop_and_the_walk_leg_runs(tmp_path, monkeypatch):
    fake = FakeServer(patch_clock(monkeypatch))
    S = fake_session(tmp_path, fake, walk_bouts=("B5",), rest_one={"B5": 180.0})
    st = S.bout("B5", 8.0, 10.0)
    assert abs(st["rest_end_age"] - (10.0 - L.STOP_LEAD_H - 1.0 / 60)) < 1e-9
    w = st["walk"]
    assert w["age1"] >= w["age0"] + L.WALK_M / 60.0 - 1e-9 and len(w["walks"]) >= 2 and w["moving_polls"] > 0
    assert ("client", "player.stop", "") in fake.cmds
    assert st["walk_summary"]["walks"] == len(w["walks"])
