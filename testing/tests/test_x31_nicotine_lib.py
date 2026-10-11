"""x31_nicotine_lib and x31_grade (Plan 11f Task 8): the nicotine chain's calendar, the replay's nicotine events (the
smoke and seed markers, the anchor edits placed off the ring), the withdrawal reading, the factor the grade reads
against the kernel's formula, and the smoke gate's loop (it passes on a fall and stops the scenario without one). Pure
Python and the lupa host: no game. Every loop runs on a fake clock (ruling T7-2)."""
import os
import sys
import types

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                          # testing/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x31_nicotine_lib as L   # noqa: E402
import x31_grade as G          # noqa: E402
from pzt.session import Timeline   # noqa: E402

RL = L.RL
START = 40.0
NW = L.NW
PATHS = ("satiety.nicH", "satiety.t", "satiety.P")


def test_the_calendar_and_the_schedule():
    kinds = {}
    for age, kind, label, extra in L.SCHEDULE:
        kinds.setdefault(kind, []).append((label, age))
    assert [x[0] for x in kinds["maint"]] == ["D0_13", "D0_20"]
    assert len(kinds["request"]) == 11 and kinds["request"][-1][0] == "D4_13"
    assert kinds["fade"] == [("FADE", 80.0)] and kinds["t2f"] == [("T2F", 86.0)] and kinds["smoke"] == [("SMOKE2", 90.0)]
    ages = [x[0] for x in L.SCHEDULE]
    assert ages == sorted(ages)
    assert abs(L.RISE_THRESHOLD_H - 5.5556) < 1e-4 and abs(L.RISE_RATE_PER_H - 0.01125) < 1e-12


def w_at(m, rise_from=30, smoke_at=None):
    """A synthetic withdrawal: 0 until minute rise_from, then 0.01125 a game hour, capped at 0.51; 0 again from
    smoke_at."""
    if smoke_at is not None and m >= smoke_at:
        return 0.0
    if m < rise_from:
        return 0.0
    return min(0.51, 0.3 + 0.01125 * (m - rise_from) / 60.0)


def live_arm(n, edits, smoke_at=None, nic_max=None):
    """The 'live' run: a fresh record stepped n minutes from START, the stat set before each drain by a stat event,
    the anchor edits as minute-keyed setpath events. Returns (rows, ring): rows[k] the state drain k left, ring[k] the
    row sampled before drain k (the stat it was fed, the record drain k-1 left)."""
    ages = [START + (k + 1) / 60.0 for k in range(n)]
    ev = [{"minute": k, "kind": "stat", "stat": NW, "value": w_at(k, smoke_at=smoke_at)} for k in range(n)]
    for m, kind, value in edits:
        ev.append({"minute": m, "kind": "setpath", "path": "satiety.nicH", "value": value})
    be = RL.ServerReplay(start=None, user="admin", sleep_allowed=False, hour_offset=7.0)
    if nic_max is not None:
        be.K.satiety.NIC_MAX = nic_max
    rows = RL.run(be, ages, ev, PATHS, start_age=START)
    ring = []
    for k in range(n):
        r = {"s": k, "age": ages[k], NW: w_at(k, smoke_at=smoke_at), "on": True}
        if k > 0:
            for p in PATHS + ("HUNGER",):
                r[p] = rows[k - 1].get(p)
        ring.append(r)
    return rows, ring


def replay(ring, events, nic_max=None):
    be = RL.ServerReplay(start=None, user="admin", sleep_allowed=False, hour_offset=7.0)
    if nic_max is not None:
        be.K.satiety.NIC_MAX = nic_max
    return RL.run(be, [r["age"] for r in ring], events, PATHS, start_age=START, seqs=[r["s"] for r in ring],
                  ring_rows=ring, feed=(NW,))


def test_the_edits_are_placed_off_the_ring_and_round_trip_through_the_tool():
    n = 400
    a_fade = START + 121 / 60.0
    value = a_fade - L.FADE_SET_DAYS * 24.0
    rows, ring = live_arm(n, [(120, "fade", value), (240, "t2f", None)])
    edits = [{"kind": "fade", "label": "FADE", "value": value, "before_age": START + 120.4 / 60, "after_age": START + 120.6 / 60},
             {"kind": "t2f", "label": "T2F", "value": None, "before_age": START + 240.4 / 60, "after_age": START + 240.6 / 60}]
    evs, notes = L.edit_events(ring, edits)
    assert not notes
    assert [(e["s"], e["label"], e["placement"]) for e in evs] == [(120, "edit-fade", "after_snapshot_before_drain"),
                                                                  (240, "edit-t2f", "relaid")]
    again = replay(ring, evs)
    for a, b in zip(rows, again):
        assert a["HUNGER"] == b["HUNGER"] and a["satiety.nicH"] == b["satiety.nicH"]
    # the T2-F anchor sits NIC_FADE_DAYS back from the drain that laid it; the fade's holds its value
    assert abs(rows[240]["satiety.nicH"] - (rows[240]["satiety.t"] - 182 * 24.0)) < 1e-9
    assert rows[200]["satiety.nicH"] == value


def test_the_fade_placement_branches_on_the_drain_age():
    rows = [{"s": 1, "age": 1.0, "satiety.nicH": 0.5, "satiety.t": 0.99},
            {"s": 2, "age": 1.02, "satiety.nicH": 0.5, "satiety.t": 1.0},
            {"s": 3, "age": 1.04, "satiety.nicH": -9.0, "satiety.t": 1.02},
            {"s": 4, "age": 1.06, "satiety.nicH": -9.0, "satiety.t": 1.04}]
    ev = lambda b, a: [{"kind": "fade", "label": "F", "value": -9.0, "before_age": b, "after_age": a}]  # noqa: E731
    e, _ = L.edit_events(rows, ev(1.010, 1.015))
    assert e[0]["s"] == 2 and e[0]["placement"] == "after_snapshot_before_drain" and e[0]["hold"] == [3]
    e, _ = L.edit_events(rows, ev(1.025, 1.03))
    assert e[0]["s"] == 3 and e[0]["placement"] == "before_snapshot_after_drain" and e[0]["hold"] == [3, 4]
    e, notes = L.edit_events(rows, ev(1.015, 1.025))
    assert e[0]["s"] == 2 and e[0]["placement"] == "ambiguous" and e[0]["hold"] == [3, 4] and notes


def test_the_smoke_and_the_seed_are_markers_at_the_rows_that_show_them():
    rows = [{"s": 1, "age": 1.0, L.EATS: 3, NW: 0.0}, {"s": 2, "age": 1.02, L.EATS: 4, NW: 0.0},
            {"s": 3, "age": 1.04, L.EATS: 4, NW: 0.2}, {"s": 4, "age": 1.06, L.EATS: 5, NW: 0.0},
            {"s": 5, "age": 1.08, L.EATS: 6, NW: 0.0}]
    eats = [{"label": "M0", "food": L.MIX650, "landed": True},
            {"label": "G_SMOKE", "food": L.CIG, "smoke": True, "landed": False, "eats_rose": 1},
            {"label": "M1", "food": L.UNIT50, "landed": True}]
    ev, notes = L.build_events(rows, eats, [])
    assert not notes
    assert [(e["s"], e["kind"], e.get("label")) for e in ev] == [(2, "eat", "M0"), (4, "stat", "smoke"), (5, "eat", "M1")]
    assert ev[1]["stat"] == NW and ev[1]["value"] == 0.0 and ev[1]["smoke"] == "G_SMOKE"
    assert [(e["s"], e["value"]) for e in L.seed_events(rows, 1.01)] == [(3, 0.2)]
    assert L.seed_events(rows, None) == []


def test_the_withdrawal_reading_reads_the_threshold_slope_and_cap():
    rows = []
    for m in range(0, 60 * 60):
        a = 10.0 + m / 60.0
        h = a - 10.0
        w = 0.0 if h < 5.556 else min(0.51, 0.01125 * (h - 5.556))
        rows.append({"s": m, "age": a, NW: w})
    (x,) = L.withdrawal_reading(rows, [10.0])
    assert abs(x["first_above_0"]["h_after_smoke"] - 5.5667) < 0.02
    assert abs(x["slope_per_h"] - 0.01125) < 1e-9
    assert abs(x["at_cap"]["h_after_smoke"] - (5.556 + 0.51 / 0.01125)) < 0.05


def test_the_grade_reads_the_factor_against_the_kernel_formula():
    n = 300
    a_fade = START + 101 / 60.0
    value = a_fade - L.FADE_SET_DAYS * 24.0
    rows, ring = live_arm(n, [(100, "fade", value), (200, "t2f", None)])
    edits = [{"kind": "fade", "label": "FADE", "value": value, "before_age": START + 100.4 / 60, "after_age": START + 100.6 / 60},
             {"kind": "t2f", "label": "T2F", "value": None, "before_age": START + 200.4 / 60, "after_age": START + 200.6 / 60}]
    evs, _ = L.edit_events(ring, edits)
    rep = replay(ring, evs)
    nf = replay(ring, evs, nic_max=0)

    def lab(rs):
        return {ring[k + 1]["s"]: dict(r, s=ring[k + 1]["s"]) for k, r in enumerate(rs) if k + 1 < len(ring)}
    S = types.SimpleNamespace(rep_by=lab(rep), nf_by=lab(nf), prev_of={b["s"]: a for a, b in zip(ring, ring[1:])},
                              hold=G.held_rows(evs))
    xs = [G.factor_row(S, r) for r in ring[2:]]
    xs = [x for x in xs if x is not None]
    assert len(xs) > 250
    # live is the replay here (the same stand-in), so live and replay factors equal the formula to float noise
    assert max(x["rel"] for x in xs) < 1e-9 and max(x["rel_replay"] for x in xs) < 1e-9
    rg = {"seed_s": None, "smoke_s": [], "smoke_labels": [], "fade_s": evs[0]["s"], "t2f_s": evs[1]["s"]}
    by = {}
    for x in xs:
        by.setdefault(G.regime_of(x, rg), []).append(x)
    assert set(by) == {"w0", "rise", "fade_edit", "t2f"}
    assert all(abs(x["formula"] - 1.0) < 1e-12 for x in by["w0"])
    assert all(abs(x["formula"] - 1.0) < 1e-12 for x in by["t2f"])
    f = by["fade_edit"][5]
    assert abs((f["formula"] - 1) / (0.1313 * f["w"] / 0.51) - 0.5) < 1e-3
    assert all(x["factor"] > 1.07 for x in by["rise"])


class FakeClock:
    """The lib's time module, deterministic: the clock moves one wall second per server answer and by the sleep asked."""
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now

    def sleep(self, s):
        self.now += max(s, 0.01)


class FakeServer:
    """A smoke's server side: stats.all answers the stat; once the eat is queued and two polls pass, the eats counter
    rises and (when `smokes`) the stat falls by min(w, 0.51); setany writes the stat."""
    def __init__(self, clock, smokes=True):
        self.clock, self.smokes = clock, smokes
        self.w, self.eats, self.age = 0.0, 10, 4.3
        self.queued, self.polls = False, 0
        self.cmds = []

    def answer(self, cmd, args):
        self.clock.now += 1.0
        self.age += 1.0 / 60
        self.cmds.append((cmd, args))
        if cmd == "eat.action":
            self.queued = True
            return {"queued": True, "fraction": 1}
        if cmd == "lua.read":
            if self.queued:
                self.polls += 1
                if self.polls == 3:
                    self.eats += 1
                    if self.smokes:
                        self.w = max(0.0, self.w - 0.51)
            vals = {"NutritionRevamp.server.intake.stats.eats": self.eats, "NutritionRevamp.server.intake.stats.landed": 7,
                    "NutritionRevamp.server.intake.stats.sips": 0, "NutritionRevamp.server.intake.stats.failures": 0}
            return {"ok": True, "values": {p: vals.get(p) for p in args.split()[1:]}}
        if cmd == "stats.all":
            return {"worldAge": self.age, "stats": {NW: self.w, "HUNGER": 0.2}}
        if cmd == "stats.setany":
            self.w = float(args.split()[2])
            return {"ok": True, "after": self.w}
        if cmd == "time.snapshot":
            return {"worldAge": self.age, "hour": 11, "minutes": 0, "mult": 1}
        if cmd == "witness.fields":
            return {"fields": {"getTimeSinceLastSmoke": 0.0}}
        return {"after": 0}


def gate_session(tmp_path, fake):
    S = object.__new__(L.Session)
    S.out = {"phase_walls": {}, "phase_errors": {}, "notes": [], "phases": {"X": {}}, "deviations": [], "steps": [],
             "verdicts": {}}
    S.tl, S.t0, S.cur = Timeline(), fake.clock.now, "X"
    S.path = str(tmp_path / "doc.json")
    S.server, S.clients = None, {}
    S.stops, S.marks, S.speeds, S.eats = [], [], [], []
    S.budget_s = 1e9
    S.seed_age = None

    def step(name, side, cmd, args="", timeout=30, log=True):
        w = S.wall()
        return {"step": name, "side": side, "cmd": cmd, "args": args, "phase": S.cur, "wall_before": w,
                "wall_after": w + 0.2, "took": 0.2, "ack": fake.answer(cmd, args)}
    S.step = step
    S.check = lambda: None
    S.one = lambda tag="one": {}
    S.spawn = lambda full, n=1, tag="spawn": {"add": {"ok": True}, "seen": {"resolved": "1"}}
    return S


def test_the_gate_passes_when_the_seeded_stat_falls(tmp_path, monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(L, "time", types.SimpleNamespace(time=clock.time, sleep=clock.sleep))
    monkeypatch.setattr(L, "POLL_S", 0.0)
    fake = FakeServer(clock)
    S = gate_session(tmp_path, fake)
    S.gate()
    st = S.stops[-1]
    assert st["kind"] == "smoke" and st["smoked"] is True and abs(st["fall"] - 0.2) < 1e-12
    assert S.out["verdicts"]["GATE"]["verdict"] == "as_predicted"
    assert ("stats.setany", "admin NICOTINE_WITHDRAWAL 0.2") in fake.cmds
    assert S.eats[-1] is st and st["eats_rose"] == 1


def test_a_smoke_that_never_lands_fails_the_gate_and_stops_the_scenario(tmp_path, monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(L, "time", types.SimpleNamespace(time=clock.time, sleep=clock.sleep))
    monkeypatch.setattr(L, "POLL_S", 0.0)
    fake = FakeServer(clock, smokes=False)
    S = gate_session(tmp_path, fake)
    with pytest.raises(L.Budget):
        S.gate()
    assert S.stops[-1]["smoked"] is False and S.stops[-1]["reason"] == "cap"
    assert S.out["verdicts"]["GATE"]["verdict"] == "falsified"


def test_the_next_day_intake_reads_the_oracles_mapping():
    def m(label, h, hn, f):
        return {"label": label, "factor": {"HUNGER": h, "HUNGER_replay": h, "HUNGER_nofactor": hn, "formula": f,
                                           "factor": h / hn, "factor_replay": h / hn, "w": 0.51, "d": 2.0,
                                           "capped": False}}
    meals = [m("D2_13", 0.3, 0.27, 1.11), m("D2_20", 0.339, 0.3, 1.13), m("D3_08", 0.226, 0.2, 1.13),
             m("D3_13", 0.2825, 0.25, 1.13)]
    x = G.next_day(meals)
    assert abs(x["live"] - 0.8475 / 0.75) < 1e-12 and x["labels"] == ["D2_20", "D3_08", "D3_13"]
    assert x["within_2pct_of_pin"] is True and [p["label"] for p in x["per_meal"]] == list(G.NEXT_DAY)
    assert G.next_day(meals[:2])["live"] is None
