"""x29_exercise_lib (Plan 11f Task 6): the replay's activity and setpath events read off the ring, shown by a round
trip through tools/replay_live.py's server backend (a replay arm with known activity is read back as a ring, its
events derived, and a second arm on the derived events reproduces it), the decay reading, the chain's calendar and
x28's F-T5-2 paths kept. Pure Python on the lupa host: no game."""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))                          # testing/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))
sys.path.insert(0, os.path.join(REPO, "tools"))

import replay_live as RL   # noqa: E402
import x29_exercise_lib as L   # noqa: E402
from pzt.session import Timeline   # noqa: E402

PATHS = ("satiety.S", "satiety.L", "satiety.t", "body.met", "body.metMinDay", "body.band2Day", "body.exKcalDay",
         "body.fm", "body.lm", "body.energyState", "body.trail.c.ex")
# a known activity (the engine rate, the exercise flag): LightWork and DefaultExercise both bill 3.0, MediumWork 4.0
# and JumpFence too; HeavyWork exercising (resistance) and not (aerobic); FitnessHeavy; Running10kmh; idle
TRUTH = [(10, 3.2, False), (14, 3.0, False), (18, 3.9, True), (22, 4.0, True), (26, 6.0, True), (34, 9.0, True),
         (40, 6.0, False), (44, 6.9, False), (48, 1.5, False), (70, 5.5, True), (75, 1.5, False)]


def arm(events, minutes=150):
    return RL.replay_arm(events, minutes=minutes, start_age=10.0, paths=PATHS, backend="server", sleep_allowed=False)[0]


def truth_events():
    return [{"minute": m, "kind": "activity", "rate": r, "exercising": x, "moving": False} for m, r, x in TRUTH]


def test_the_activity_read_off_the_ring_reproduces_it():
    rows = arm(truth_events())
    # an arm row s = j is the state step j - 1 left, as a ring row k reads drain k - 1's: the ring's own phase
    ev, unknown = L.activity_events(rows)
    assert unknown == []
    back = [{"minute": e["s"], "kind": "activity", "rate": e["rate"], "exercising": e["exercising"], "moving": False}
            for e in ev]
    again = arm(back)
    for a, b in zip(rows, again):
        for p in PATHS:
            assert a.get(p) == b.get(p), (a["s"], p, a.get(p), b.get(p))
    got = {e["s"]: (e["rate"], e["class"]) for e in ev}
    assert got[10] == (3.2, "LightWork") and got[14] == (3.0, "DefaultExercise")
    assert got[18] == (3.9, "MediumWork") and got[22] == (4.0, "JumpFence")
    assert max(r["satiety.S"] for r in rows) > 0.05                   # the vigorous minutes moved the acute state


def test_rate_for_prefers_the_idle_class_among_the_unbilled():
    assert L.rate_for(1.3, None, 6.0) == ("Default", 1.5)
    assert L.rate_for(1.3, 1.5, 6.0) == ("Default", 1.5)
    assert L.rate_for(6.0, None, 1.5) == ("HeavyWork", 6.0)
    assert L.rate_for(3.0, 3.21, 1.5) == ("LightWork", 3.2)
    assert L.rate_for(7.77, None, 1.5) == (None, None)


def test_the_setpath_event_and_the_decay_reading():
    m = 40
    ev = [{"minute": m, "kind": "setpath", "path": "satiety.S", "value": 1.0}]
    rows = arm(ev, minutes=120)
    sp = [{"label": "SET", "value": 1.0, "ok": True, "age_before": rows[m - 1]["age"]}]
    out, notes = L.setpath_events(rows, sp)
    assert notes == [] and [e["s"] for e in out] == [m]
    d = L.decay_reading(rows, out, 0.15)
    assert len(d) == 1 and d[0]["ok"] and d[0]["graded"] > 40 and d[0]["max_rel"] < 1e-9
    # a set read exactly at a row (the set before that row's sample) is due at that row
    rows2 = [dict(r) for r in rows]
    rows2[m]["satiety.S"] = 1.0
    out2, _ = L.setpath_events(rows2, sp)
    assert [e["s"] for e in out2] == [rows2[m]["s"]]


def test_the_leg_reading_counts_the_vigorous_minutes():
    rows = arm(truth_events())
    r = L.leg_reading(rows, 10.0, 12.5)
    assert r["met_max"] == 9.3 and r["S_rises"] > 0 and r["minutes_at_or_over_6"] > 0
    assert abs(r["exKcal_rise"] - rows[-1]["body.exKcalDay"]) < 1e-9


def test_the_chain_calendar():
    kinds = {}
    for age, kind, label in L.SCHEDULE:
        kinds.setdefault(kind, []).append(label)
    assert kinds["bout"] == ["B0", "B1", "B2", "B3", "B4", "B5", "B6"]
    assert kinds["maint"][:3] == ["D0_13", "D0_20", "D1_08"] and kinds["maint"][-1] == "D7_13"
    assert L.END_CHAIN - L.FIRST_BOUT == 7 * 24 + 0.5          # 15:30 on day 7
    assert all(a <= b for a, b in zip([x[0] for x in L.SCHEDULE], [x[0] for x in L.SCHEDULE][1:]))


def bare(tmp_path):
    S = object.__new__(L.Session)
    S.out = {"phase_walls": {}, "phase_errors": {}, "notes": [], "phases": {}}
    S.tl, S.t0, S.cur = Timeline(), time.time(), "pre"
    S.path = str(tmp_path / "doc.json")
    S.server, S.clients = None, {}
    return S


def test_a_budget_stop_reaches_the_read_back_and_the_flush(tmp_path):
    S = bare(tmp_path)
    calls = []
    for name in ("S", "H", "W", "R", "D", "Z"):
        setattr(S, "phase_" + name, (lambda n: (lambda: calls.append(n)))(name))

    def over(_S):
        calls.append("X")
        raise L.Budget("wall past the budget")
    S.scenario = over
    S.body()
    assert calls == ["S", "H", "W", "X", "R", "D", "Z"]
    assert S.out["budget_stop"]["phase"] == "X"


def test_the_activity_round_trip_in_the_rings_own_phase():
    # a clock-only ring replayed live with known activity and a setpath; its rows relabelled as the ring (ring row s
    # reads the state drain s - 1 left, as the harness's H2 samples); the events derived off it are the known ones, and
    # a second live replay on them reproduces S, L, the billed MET and the exercise kcal exactly
    import json
    with open(os.path.join(REPO, "testing", "artifacts", "x281-20261011-033356", "start.json"), encoding="utf-8") as fh:
        start = json.load(fh)
    t0 = start["rec"]["satiety"]["t"]
    paths = list(L.RING_RECORD)
    clock = [{"s": i + 1, "age": t0 + (i + 1) / 60.0, "dtM": 1.0, "on": True} for i in range(200)]
    truth = [(20, 3.2, False), (25, 3.0, False), (30, 6.0, True), (45, 9.0, True), (55, 6.9, False), (60, 1.5, False),
             (100, 6.0, False), (110, 1.5, False)]
    ev = [{"s": s, "kind": "activity", "rate": r, "exercising": x, "moving": False} for s, r, x in truth]
    ev.append({"s": 150, "kind": "setpath", "path": "satiety.S", "value": 1.0})
    out, _ = RL.replay_live(clock, ev, start, paths=paths, sleep_allowed=False)
    by = {r["s"]: r for r in out}
    ring = []
    for c in clock[1:]:
        r = dict(by[c["s"]])
        r.update(c)
        ring.append(r)
    acts, unknown = L.activity_events(ring)
    sp, notes = L.setpath_events(ring, [{"label": "x", "value": 1.0, "ok": True, "age_before": ring[147]["age"]}])
    assert unknown == [] and notes == []
    assert [(e["s"], e["rate"], e["exercising"]) for e in acts] == truth
    assert [e["s"] for e in sp] == [150]
    out2, _ = RL.replay_live(ring, acts + sp, start, paths=paths, sleep_allowed=False)
    by2 = {r["s"]: r for r in out2}
    for r in ring[1:]:
        for p in ("satiety.S", "satiety.L", "body.met", "body.exKcalDay", "body.trail.c.ex"):
            assert by2[r["s"]].get(p) == r.get(p), (r["s"], p)
