"""x36_gut_lib and x36_grade (Plan 11g Task 8): the live checks of the final satiety and deficit model. The ring (the
meal pool M, the buffer, the fills, the server's held energy level); the food fill on the mod's own kernel; the graded
diff with its floor; a meal's time course and a drink's fills graded on a synthetic live ring made by the mod's own
server replay (the ring's own phase: ring row s reads the state drain s - 1 left), with the grade shown to bite on a
moved HUNGER, M or fill; the day read and the REST arm; the energy pairs' grade (equal, lag inside the push gap,
mismatch) and the ring's level steps; the course and the energy pair on a fake server and clock (ruling T7-2). Pure
Python on the lupa host: no game."""
import json
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))                          # testing/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))
sys.path.insert(0, os.path.join(REPO, "tools"))

import replay_live as RL   # noqa: E402
import x36_gut_lib as L   # noqa: E402
import x36_grade as G   # noqa: E402
import x362_surplus as D2   # noqa: E402
from pzt.session import Timeline   # noqa: E402


def K():
    return L._kh_static().K


# --- the ring --------------------------------------------------------------------------------------------------------

def test_the_ring_reads_the_meal_pool_the_buffer_and_the_held_level():
    paths = list(L.RING_RECORD) + list(L.RING_GLOBALS)
    assert len(paths) == 30 <= 32 and len(set(paths)) == 30
    assert L.MPOOL == "satiety.M" and L.MPOOL in L.RING_RECORD
    assert not any(p in ("satiety.P", "satiety.G") for p in paths)
    assert {L.FILL, L.LIQ, L.BUF_KCAL} <= set(L.RING_RECORD)
    assert all("stomach.buffer." + k in L.RING_RECORD for k in L.BUF_KEYS)
    assert L.LASTSIG in L.RING_GLOBALS and L.LASTSIG.endswith("lastSig.admin")
    assert float(K().stomach.CAPACITY_MAX_G) == 730.0


def test_the_food_fill_is_the_kernels_solid_lane_over_the_capacity():
    row = {"stomach.buffer.water": 300.0, "stomach.buffer.proteins": 24.375, "stomach.buffer.carbs": 81.25,
           "stomach.buffer.lipids": 25.277778, "stomach.buffer.fibre": 6.0}
    assert abs(L.food_fill(row) - 436.902778 / 730.0) < 1e-12
    row["stomach.buffer.water"] = 2000.0
    assert L.food_fill(row) == 1.0
    del row["stomach.buffer.fibre"]
    assert L.food_fill(row) is None


def test_the_energy_digit_is_the_signatures_thousands():
    assert L.energy_digit(12100) == 2 and L.energy_digit(1000.0) == 1 and L.energy_digit(999) == 0
    assert L.energy_digit(None) is None and L.energy_digit(True) is None


# --- a synthetic live ring: the mod's own server replay ---------------------------------------------------------------

def start_record():
    with open(os.path.join(REPO, "testing", "artifacts", "x281-20261011-033356", "start.json"), encoding="utf-8") as fh:
        return json.load(fh)


def synth(events, n=420):
    """(ring, start): ring rows as the harness samples them, from the mod's own server replay of `events`."""
    start = start_record()
    t0 = start["rec"]["satiety"]["t"]
    clock = [{"s": i + 1, "age": t0 + (i + 1) / 60.0, "dtM": 1.0, "on": True, "ev": i + 1, "drained": i}
             for i in range(n)]
    out = RL.replay_live(clock, events, start, paths=list(L.RING_RECORD), sleep_allowed=False, ring_activity=False)[0]
    by = {r["s"]: r for r in out}
    ring = []
    for c in clock[1:]:
        r = dict(by[c["s"]])
        r.update(c)
        ring.append(r)
    return ring, start


EAT_S = 30


def course_ring():
    return synth([{"s": EAT_S, "kind": "eat", "food": L.MIX650, "label": "C650"}])


def test_a_course_on_its_own_replay_passes_and_reads_the_pool_and_the_fills():
    ring, _ = course_ring()
    rep = [dict(r) for r in ring]
    a0 = next(r["age"] for r in ring if r["s"] == EAT_S)
    cr = L.course_reading(ring, rep, a0, ring[-1]["age"])
    assert cr["ok"] and cr["diff"]["ok"]
    assert all(cr["diff"]["fields"][f]["n"] > 300 for f in L.TOL_GRADE)
    before = next(r for r in ring if r["s"] == EAT_S)                  # ring row s reads the state drain s - 1 left
    after = [r for r in ring if r["s"] > EAT_S]
    m = [r[L.MPOOL] for r in after]
    assert m[0] > before[L.MPOOL] + 600 and m[-1] < m[0]                 # fed at the eat, cleared after
    ff = [L.food_fill(r) for r in after]
    assert L.food_fill(before) == 0.0 and ff[0] > 0.5 and ff[-1] < ff[0]
    assert all(abs(r[L.FILL] - L.food_fill(r)) < 1e-6 for r in after)   # no drink: the physical fill is the food fill
    assert cr["series"][0]["minute"] == 0.0 and cr["series"][1][L.MPOOL] is not None
    assert cr["nadir"]["live"]["minute"] >= 0


def test_the_course_grade_bites_on_hunger_the_pool_and_the_fill():
    ring, _ = course_ring()
    a0 = next(r["age"] for r in ring if r["s"] == EAT_S)
    for field, d in (("HUNGER", 0.0025), (L.MPOOL, None), ("stomach.buffer.water", 2.0)):
        rep = [dict(r) for r in ring]
        r = rep[EAT_S + 60]
        r[field] = r[field] * 1.01 if d is None else r[field] + d
        cr = L.course_reading(ring, rep, a0, ring[-1]["age"])
        assert cr["ok"] is False, field
    rep = [dict(r) for r in ring]
    rep[EAT_S + 60][L.MPOOL] += 0.5                                      # under 0.5 % of a pool over 100
    assert L.course_reading(ring, rep, a0, ring[-1]["age"])["ok"] is True


def test_the_floor_holds_a_relative_bound_near_zero():
    rep = [{"s": 1, "age": 1.0, "x": 0.2}, {"s": 2, "age": 1.1, "x": 0.0}]
    live = [{"s": 1, "age": 1.0, "x": 0.25}, {"s": 2, "age": 1.1, "x": 0.4}]
    assert L.diff_floor(rep, live, {"x": ("rel", 0.5, 1.0)})["ok"]
    bad = L.diff_floor(rep, live, {"x": ("rel", 0.5, 0.0)})
    assert not bad["ok"] and bad["fields"]["x"]["over"] == 1     # 0.25 of 0.2 is inside; 0.4 over 0 is not
    rep[1]["between"] = True
    w = L.diff_floor(rep, live, {"x": ("abs", 0.1)}, window=(0.9, 1.05))
    assert w["fields"]["x"]["n"] == 1 and w["classes"]["between"] == 0


def test_a_water_drink_lifts_the_physical_fill_and_never_the_food_fill():
    ring, _ = synth([{"s": 20, "kind": "drink", "fluid": "Water", "litres": 0.5, "label": "W500"}], n=90)
    rep = [dict(r) for r in ring]
    x = L.drink_reading(ring, rep, [20], ring[-1]["age"])
    assert 0.6 < x["peak_fill"] <= 0.69 and x["peak_fill"] == x["peak_fill_replay"]
    assert x["food_fill_rise_max"] <= 1e-12
    assert max(L.food_fill(r) for r in ring) <= 1e-12


# --- the day and the REST arm -----------------------------------------------------------------------------------------

def test_the_day_reading_is_time_weighted_and_reads_named_ages():
    rows = [{"s": i, "age": 10.0 + i / 60.0, "HUNGER": 0.1 if i <= 60 else 0.3} for i in range(0, 121)]
    d = L.day_reading(rows, 10.0, 12.0, (10.5, 11.5))
    assert abs(d["mean"] - 0.2) < 1e-9 and d["points"] == [0.1, 0.3] and abs(d["points_mean"] - 0.2) < 1e-12
    assert L.day_reading(rows, 10.0, 12.0, (10.5, 50.0))["points_mean"] is None


def test_the_rest_arm_swaps_the_surplus_meals_for_maintenance_portions():
    ev = [{"s": 5, "kind": "eat", "food": L.MIX650, "label": "D0_12_0"},
          {"s": 50, "kind": "eat", "food": L.MIX650, "label": "S1_07_0"},
          {"s": 51, "kind": "eat", "food": L.MIX650, "label": "S1_07_1"},
          {"s": 52, "kind": "eat", "food": L.MIX217, "label": "S1_07_2"},
          {"s": 53, "kind": "autodrop", "g": 100.0, "label": "autodrop"}]
    out, meals = L.rest_arm_events(ev, [], {"S1_07"}, 800.0)
    assert [e["label"] for e in out if e["kind"] == "eat"] == ["D0_12_0"] + ["REST_S1_07_%d" % i for i in range(4)]
    assert all(e["s"] == 50 for e in out if str(e["label"]).startswith("REST_"))
    assert meals == [{"label": "S1_07", "s": 50, "portions": {L.MIX650: 1, L.MIX217: 0, L.UNIT50: 3}, "kcal": 800.0}]
    assert any(e["kind"] == "autodrop" for e in out)


def test_karl_points_take_the_row_before_each_meal_and_its_last_landing():
    ring = [{"s": s, "age": 20.0 + s / 60.0} for s in range(1, 400)]
    eats = [{"stop": m, "ring_s": s} for m, ss in (("S1_07", (100, 102)), ("S1_12", (200,)), ("S1_18", (300, 301)))
            for s in ss]
    ages, notes = D2.karl_points(ring, eats)
    assert not notes and len(ages) == 8
    assert ages[:2] == [20.0 + 99 / 60.0, 20.0 + 102 / 60.0] and list(D2.WALK_AGES) == [L.at(1, 8.0), L.at(1, 9 + 4 / 60.0)]


# --- the energy pairs and the ring's levels ---------------------------------------------------------------------------

def ep(tag, sw, s_lv, c_lv, gap=0.2):
    return {"tag": tag, "age": sw / 10.0, "server_wall": sw, "client_wall": sw - gap, "wall_gap": gap,
            "server_level": s_lv, "client_level": c_lv}


def test_the_energy_pairs_allow_the_push_gap_and_bite_past_it():
    ok = [ep("a", 10, 0, 0), ep("b", 20, 1, 0), ep("c", 60, 1, 0), ep("d", 85, 1, 1)]
    g1 = L.energy_pairs_grade(ok)
    assert g1["ok"] and (g1["equal"], g1["lag"], g1["mismatch"]) == (2, 2, 0) and g1["changes"][0]["to"] == 1
    late = [ep("a", 10, 0, 0), ep("b", 20, 1, 0), ep("c", 90, 1, 0)]
    assert L.energy_pairs_grade(late)["mismatch"] == 1 and not L.energy_pairs_grade(late)["ok"]
    wrong = [ep("a", 10, 1, 2)]
    assert not L.energy_pairs_grade(wrong)["ok"]
    far = [ep("a", 10, 0, 0, gap=1.5)]
    assert not L.energy_pairs_grade(far)["ok"]
    down = [ep("a", 10, 1, 1), ep("b", 20, 0, 0)]
    assert L.energy_pairs_grade(down)["steps_down"] == 1 and not L.energy_pairs_grade(down)["ok"]


def test_the_ring_levels_read_the_signature_digit():
    ring = [{"s": 1, "age": 1.0, L.LASTSIG: 0}, {"s": 2, "age": 2.0, L.LASTSIG: 1000},
            {"s": 3, "age": 3.0}, {"s": 4, "age": 4.0, L.LASTSIG: 11000}, {"s": 5, "age": 5.0, L.LASTSIG: 10000}]
    r = L.ring_levels(ring)
    assert [(c["from"], c["to"]) for c in r["changes"]] == [(0, 1), (1, 0)] and r["steps_down"] == 1 and r["last"] == 0


# --- the course and the energy pair on a fake server and clock -------------------------------------------------------

class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now

    def sleep(self, s):
        self.now += max(s, 0.01)


class FakeServer:
    """Each answer advances the world one game minute. HUNGER falls from 0.25 to 0.05 over the first hour after the
    start and rises 0.001 a minute after; the server's signature holds level 1 from age 9.0."""

    def __init__(self, clock, age=6.0):
        self.clock, self.age, self.a0 = clock, age, age
        self.cmds = []

    def h(self):
        m = (self.age - self.a0) * 60
        return 0.25 - 0.2 * m / 60 if m < 60 else 0.05 + 0.001 * (m - 60)

    def answer(self, side, cmd, args):
        self.clock.now += 0.3
        self.age += 1.0 / 60
        self.cmds.append((side, cmd, args))
        if cmd == "stats.all":
            return {"worldAge": self.age, "stats": {"HUNGER": self.h(), "THIRST": 0.1}}
        if cmd == "time.snapshot":
            return {"worldAge": self.age, "hour": 13, "minutes": 0, "mult": 1}
        if cmd == "lua.read":
            paths = args.split()[1:]
            lv = 1 if self.age >= 9.0 else 0
            v = {L.CLI_ENERGY[0]: lv, L.CLI_ENERGY[1]: 1.1, L.CLI_ENERGY[2]: lv, L.CLI_ENERGY[3]: lv,
                 L.CLI_ENERGY[4]: 3, L.SRV_ENERGY[0]: 1000 * lv + 10000, L.SRV_ENERGY[1]: 2, "body.energyState": 1.1}
            return {"ok": True, "values": {p: v.get(p) for p in paths}}
        return {"ok": True}


def fake_session(tmp_path, fake):
    S = object.__new__(L.Session)
    S.out = {"phase_walls": {}, "phase_errors": {}, "notes": [], "phases": {"X": {}}, "deviations": [], "steps": [],
             "verdicts": {}, "readings": {}}
    S.tl, S.t0, S.cur = Timeline(), fake.clock.now, "X"
    S.path = str(tmp_path / "doc.json")
    S.run_dir = str(tmp_path)
    S.server, S.clients, S.started = None, {}, []
    S.stops, S.marks, S.speeds, S.eats, S.drinks, S.pairs, S.epairs, S.courses = [], [], [], [], [], [], [], []
    S.budget_s = 1e9
    S.canteen = False

    def step(name, side, cmd, args="", timeout=30, log=True):
        w = S.wall()
        return {"step": name, "side": side, "cmd": cmd, "args": args, "phase": S.cur, "wall_before": w,
                "wall_after": w + 0.1, "took": 0.1, "ack": fake.answer(side, cmd, args)}
    S.step = step
    S.check = lambda: None
    S.one = lambda tag="one": {}
    S.fast = lambda tag="fast": {}
    S.slow = lambda tag="slow": {}
    S.rcon = lambda cmd, tag: {"ok": True}
    return S


def patch_clock(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(L, "time", types.SimpleNamespace(time=clock.time, sleep=clock.sleep))
    monkeypatch.setattr(L, "POLL_S", 0.0)
    return clock


def test_a_course_runs_to_the_request_after_its_minimum(tmp_path, monkeypatch):
    fake = FakeServer(patch_clock(monkeypatch))
    S = fake_session(tmp_path, fake)
    S.eats.append({"label": "C650", "landed": True, "landed_age_polled": 6.0})
    c = S.course("C650", 4.0, 6.0, pair_every_m=60.0)
    assert c["request_age"] is not None and abs(c["request_age"] - (6.0 + (60 + 200) / 60.0)) < 0.05
    assert c["end_age"] >= c["request_age"] - 1e-9 and c["end_age"] < c["request_age"] + 0.05 and c["capped"] is False
    assert c["end_age"] >= 6.0 + 4.0                                     # the request came after the minimum
    assert [p["tag"] for p in S.pairs][:3] == ["C650_p0", "C650_p60", "C650_p120"]
    S.eats.append({"label": "C400", "landed": True, "landed_age_polled": fake.age})
    fake.a0 = fake.age + 100                                             # HUNGER never falls: capped at max_h
    c2 = S.course("C400", 1.0, 1.5)
    assert c2["capped"] is True and c2["end_age"] >= c2["a0"] + 1.5 - 1e-9


def test_the_energy_pair_reads_both_sides_in_the_same_second(tmp_path, monkeypatch):
    fake = FakeServer(patch_clock(monkeypatch))
    S = fake_session(tmp_path, fake)
    p0 = S.energy_pair("E0")
    fake.age = 9.5
    p1 = S.energy_pair("E1")
    assert p0["server_level"] == 0 and p0["client_level"] == 0 and abs(p0["wall_gap"]) <= L.PAIR_GAP_MAX_S
    assert p1["server_level"] == 1 and p1["client_level"] == 1 and p1["server_sig"] == 11000
    assert L.energy_pairs_grade(S.epairs)["ok"]


def test_the_grade_reads_the_drivers_documents():
    assert set(G.DOCS) == {"x361", "x362", "x363", "x364"} and set(G.GRADERS) == set(G.DOCS)
    assert G.MEAL650_MIN == (240.0, 300.0) and G.BREAKFAST_HOLD_MIN == 180.0 and G.LEVEL1 == 1.10
    # the energy ladder's level 1 at the last build that carried it (Plan 15 Task 9 removed the energy class; the grade
    # is frozen with its run, CLAUDE.md section 5, so it is read off a pinned commit, never HEAD)
    import re
    import subprocess
    old = subprocess.run(["git", "-C", RL.REPO, "show", "7c8725b3:mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_View.lua"],
                         capture_output=True, text=True, check=True).stdout
    first = re.search(r"K\.view\.ENERGY_AT = \{\s*([0-9.]+),", old).group(1)
    assert float(first) == G.LEVEL1


def test_the_regrade_reads_the_written_row_after_each_meal():
    import x36_regrade as RG
    ring = [{"s": s, "age": 20.0 + s / 60.0} for s in range(1, 400)]
    eats = [{"stop": m, "ring_s": s} for m, ss in (("S1_07", (100, 102)), ("S1_12", (200,)), ("S1_18", (300, 301)))
            for s in ss]
    ages, ev_rows, notes = RG.karl_points_r1(ring, eats)
    assert not notes and len(ages) == 8 and [x["last_landing_s"] for x in ev_rows] == [102, 200, 301]
    assert ages[:2] == [20.0 + 99 / 60.0, 20.0 + 103 / 60.0]           # the row after the last landing, not the landing


# --- HUNGER fidelity on a ring recorded on this build (the Task 4 and 6c review notes) --------------------------------

X361 = os.path.join(REPO, "testing", "artifacts", "x361-20261012-200722")


def test_the_gut_11g_snapshot_equals_the_shipped_constants_today():
    # GUT_11G is the constants x361 was recorded at (7093079b); it equals the shipped kernel today. A later plan that refits
    # any of them fails this test by design, and must leave GUT_11G as it is: x361 replays at it, not at the refit.
    k = K()
    assert len(RL.GUT_11G) == 14
    for name, value in RL.GUT_11G.items():
        mod, key = name.split(".")
        assert k[mod][key] == value, name


class RecordedSess(G.Sess):
    """x361's session replayed at its recording build's constants (RL.GUT_11G), not at the shipped kernel's."""

    def replay(self, events):
        rows, _ = RL.replay_live(self.ring, events, self.start, paths=self.rpaths, user=L.USER, player=self.player,
                                 start_stats=self.stats, sleep_allowed=False,
                                 constants=dict(RL.GUT_11G, **RL.PRE_CURVE))   # and its pre-curve writer (Plan 15 Task 6)
        return rows


def test_the_x361_ring_replays_within_the_default_tolerances():
    # x361 (Plan 11g Task 8) was recorded on the final build (7093079b): the meal pool M, F to the hard capacity, the
    # two fills. It replays at GUT_11G, the recording build's satiety and deficit constants (a snapshot later refits do
    # not touch, ruling T4-1's way: the 11f rings replay at DEFICIT_11F), so a later refit never turns this red. Its
    # replay reads HUNGER within 0.002, es within 0.005 and L within 0.5 % on every graded row (660 rows: 0.000101,
    # 0.000389, 0), M, the fills and the buffer within TOL_GRADE, and both courses' request minutes equal live (C650
    # 247.09, C400 215.13). Skipped until the artifact is committed (staged at Task 8, committed with its rows at Task 9).
    import pytest
    if not os.path.isdir(X361):
        pytest.skip("x361's artifact folder is not in this checkout")
    S = RecordedSess("x361", run_dir=X361)
    assert S.diff["ok"] and S.diff["fields"]["HUNGER"]["n"] == 660 and S.diff["fields"]["HUNGER"]["max"] < 0.002
    assert S.grade["ok"]
    c = G.grade_x361(S)["courses"]
    assert round(c["C650"]["request"]["live_min"], 2) == round(c["C650"]["request"]["replay_min"], 2) == 247.09
    assert round(c["C400"]["request"]["live_min"], 2) == round(c["C400"]["request"]["replay_min"], 2) == 215.13
