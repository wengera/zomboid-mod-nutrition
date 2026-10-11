"""x33_monotony_lib and x33_grade (Plan 11f Task 9): the monotony chain's calendar, the kernel twin the readings grade
against (K.monotony's own delta), the replay's mood events, the floor window, the eat's bracketing loop (the pre-add
stats are the last read whose counter read had not risen) and the grade's climb. Pure Python and the lupa host: no
game. Every loop runs on a fake clock (ruling T7-2)."""
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                          # testing/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x33_monotony_lib as L   # noqa: E402
import x33_grade as G          # noqa: E402
from pzt.session import Timeline   # noqa: E402

RL = L.RL


def K():
    return L._kh_static().K


def test_the_calendar_and_the_ring():
    monos = [(label, age, extra) for age, kind, label, extra in L.SCHEDULE if kind == "mono"]
    assert [m[0] for m in monos] == ["M0", "S0", "M1", "S1", "M2", "S2", "M3", "S3", "M4", "S4"]
    assert all(m[2] == (L.MONO if m[0][0] == "M" else L.STAPLE) for m in monos)
    assert [m[1] for m in monos if m[0][0] == "M"] == [6.0, 30.0, 54.0, 78.0, 102.0]
    ages = [x[0] for x in L.SCHEDULE]
    assert ages == sorted(ages)
    assert len(L.RING_RECORD) + len(L.RING_GLOBALS) <= 32
    assert "monotony.t.[TKX.Mono450].n" in L.RING_RECORD and L.UTARGET in L.RING_RECORD


def test_the_kernel_twin_is_the_kernels_level_right_after_a_whole_portion():
    # the lib was run on the add at the eat (Plan 11f Task 9, commit 6a6cdb61); since Task 9b (ruling T9-1) the kernel
    # holds a floor at the type's level instead, which for a whole portion under the cap is the twin's delta
    k = K()
    m = k.monotony.new()
    nb, last = None, None
    for i, age in enumerate((0.0, 23.9, 48.2, 72.0, 96.5)):
        d_py, c, n = L.kernel_delta(k, nb, last, age, False)
        e = k.monotony.record(m, "TKX.Mono450", age, 1, False)
        assert abs(k.monotony.level(e, age) - d_py) < 1e-12
        assert abs(e.n - n) < 1e-12
        nb, last = e.n, e.last
    assert abs(L.nominal_delta(k, 4, False) - 9.978) < 1e-3
    assert abs(L.nominal_delta(k, 4, True) - 2.4945) < 1e-3
    assert L.nominal_delta(k, 0, False) == 0.0
    # past the window the count reads 0
    assert L.kernel_delta(k, 5.0, 0.0, 168.5, False)[1] == 0.0


def test_the_replay_books_the_study_foods_as_the_kernel_does():
    """A stand-in replay of Mono450 and Staple450 eaten twice 24 h apart: since Plan 11f Task 9b (ruling T9-1) no eat
    adds a mood, and the writer's floor holds both stats at the kernel twin's delta (the most repeated type's level)."""
    ages = [1.0 + h for h in range(0, 30)]
    ev = [{"age": 3.0, "kind": "eat", "food": L.MONO}, {"age": 4.0, "kind": "eat", "food": L.STAPLE},
          {"age": 27.0, "kind": "eat", "food": L.MONO}, {"age": 28.0, "kind": "eat", "food": L.STAPLE}]
    be = RL.ServerReplay(start=None, user="admin", sleep_allowed=False, hour_offset=7.0)
    RL.run(be, ages, ev, (), start_age=0.0)
    log = [x for x in be.eats if x["kind"] == "eat"]
    assert [x["fullType"] for x in log] == [L.MONO, L.STAPLE, L.MONO, L.STAPLE]
    assert all(x["unhappy"] == 0 and x["boredom"] == 0 for x in log)
    d = L.kernel_delta(K(), 1.0, 3.0, 27.0, False)[0]
    rec = be.record()
    u, b = be.K.monotony.target(rec.monotony, 27.0)
    assert abs(u - d) < 1e-9 and abs(b - d) < 1e-9
    assert rec.monotony.t[L.STAPLE].s is True


def test_the_setany_events_sit_at_the_first_row_after_the_set():
    rows = [{"s": 1, "age": 1.0}, {"s": 2, "age": 1.02}, {"s": 3, "age": 1.04}]
    stops = [{"kind": "mono", "label": "M1", "set": {"before_age": 1.005, "after_age": 1.01,
                                                     "bored": {"after": 0.0}, "unhappy": {"after": 20.0}}},
             {"kind": "refill", "label": "R"}]
    ev, notes = L.setany_events(rows, stops)
    assert not notes
    assert [(e["s"], e["stat"], e["value"]) for e in ev] == [(2, "BOREDOM", 0.0), (2, "UNHAPPINESS", 20.0)]
    ev, notes = L.setany_events(rows, [{"kind": "mono", "label": "M2", "set": {"after_age": 2.0}}])
    assert ev == [] and notes


def test_the_floor_window_reads_a_fall_below_the_post_value():
    ring = [{"s": i, "age": 10.0 + i / 60.0, "UNHAPPINESS": 29.97 + (0.5 if i > 20 else 0.0), L.UTARGET: 0.0,
             "BOREDOM": 9.9} for i in range(0, 40)]
    w = L.floor_window(ring, 10.0, 29.97)
    assert w["rows"] == 30 and w["no_fall"] is True and w["fall_below_post"] == 0.0 and w["target_max"] == 0.0
    ring[5]["UNHAPPINESS"] = 25.0
    w = L.floor_window(ring, 10.0, 29.97)
    assert w["no_fall"] is False and abs(w["fall_below_post"] - 4.97) < 1e-9
    assert L.floor_window([], 10.0, 1.0) == {"rows": 0}


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now

    def sleep(self, s):
        self.now += max(s, 0.01)


class FakeServer:
    """A mono eat's two sides: setany writes the server's stats; the client copy follows one answer later; once the
    eat is queued and three counter reads pass, the landing adds `delta` to both stats in the counter read's own tick
    (so a stats.all read before that counter read is pre-add)."""
    def __init__(self, clock, delta=3.4):
        self.clock, self.delta = clock, delta
        self.srv = {"BOREDOM": 7.0, "UNHAPPINESS": 3.0}
        self.cli = dict(self.srv)
        self.landed, self.mono, self.age = 5, 2, 30.0
        self.queued, self.polls = False, 0
        self.entry = {"n": 1.0, "last": 6.0}
        self.cmds = []

    def answer(self, side, cmd, args):
        self.clock.now += 1.0
        self.age += 1.0 / 60
        self.cmds.append((side, cmd, args))
        cli_view = dict(self.cli)
        self.cli = dict(self.srv)
        if cmd == "eat.action":
            self.queued = True
            return {"queued": True, "fraction": 1}
        if cmd == "stats.setany":
            _, stat, v = args.split()
            before = self.srv[stat]
            self.srv[stat] = float(v)
            return {"ok": True, "stat": stat, "before": before, "after": float(v)}
        if cmd == "stats.all":
            st = cli_view if side == "client" else self.srv
            return {"worldAge": self.age, "stats": dict(st, HUNGER=0.3)}
        if cmd == "lua.read":
            paths = args.split()[1:]
            if args.startswith("record:"):
                return {"ok": True, "values": {p: self.entry[p.rsplit(".", 1)[-1]] for p in paths}}
            if self.queued:
                self.polls += 1
                if self.polls == 3:
                    self.landed += 1
                    self.mono += 1
                    for k in ("BOREDOM", "UNHAPPINESS"):
                        self.srv[k] += self.delta
                    self.entry = {"n": 1.79, "last": self.age}
            vals = {"NutritionRevamp.server.intake.stats.eats": self.landed,
                    "NutritionRevamp.server.intake.stats.landed": self.landed,
                    "NutritionRevamp.server.intake.stats.monotony": self.mono}
            return {"ok": True, "values": {p: vals.get(p, 0) for p in paths}}
        if cmd == "time.snapshot":
            return {"worldAge": self.age, "hour": 13, "minutes": 0, "mult": 1}
        if cmd == "foodtimer.set":
            return {"after": 0}
        return {"ok": True}


def eat_session(tmp_path, fake):
    S = object.__new__(L.Session)
    S.out = {"phase_walls": {}, "phase_errors": {}, "notes": [], "phases": {"X": {}}, "deviations": [], "steps": [],
             "verdicts": {}}
    S.tl, S.t0, S.cur = Timeline(), fake.clock.now, "X"
    S.path = str(tmp_path / "doc.json")
    S.server, S.clients = None, {}
    S.stops, S.marks, S.speeds, S.eats = [], [], [], []
    S.budget_s = 1e9

    def step(name, side, cmd, args="", timeout=30, log=True):
        w = S.wall()
        return {"step": name, "side": side, "cmd": cmd, "args": args, "phase": S.cur, "wall_before": w,
                "wall_after": w + 0.2, "took": 0.2, "ack": fake.answer(side, cmd, args)}
    S.step = step
    S.check = lambda: None
    S.one = lambda tag="one": {}
    S.spawn = lambda full, n=1, tag="spawn": {"add": {"ok": True}, "seen": {"resolved": "1"}}
    return S


def test_the_eat_brackets_the_add_and_reads_the_client(tmp_path, monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(L, "time", types.SimpleNamespace(time=clock.time, sleep=clock.sleep))
    monkeypatch.setattr(L, "POLL_S", 0.0)
    fake = FakeServer(clock)
    S = eat_session(tmp_path, fake)
    st = S.mono_eat(L.MONO, "M1", 30.0)
    assert st["landed"] is True and st["day"] == 1
    assert ("server", "stats.setany", "admin BOREDOM 0.0") in fake.cmds
    assert ("server", "stats.setany", "admin UNHAPPINESS 20.0") in fake.cmds
    assert st["pre"]["UNHAPPINESS"] == 20.0 and st["pre"]["BOREDOM"] == 0.0
    assert abs(st["post"]["UNHAPPINESS"] - 23.4) < 1e-12 and abs(st["post"]["BOREDOM"] - 3.4) < 1e-12
    assert st["client_before"]["UNHAPPINESS"] == 20.0
    assert st["monotony_counter_rose"] == 1 and st["mono_after"]["n"] == 1.79
    assert st["window_end_age"] >= st["landed_age_polled"] + L.WINDOW_M / 60.0 - 1e-9
    x = L.eat_reading(st, K())
    assert abs(x["add"]["UNHAPPINESS"] - 3.4) < 1e-12 and x["add_equal"] < 1e-12
    assert x["client_first_add"] is not None and x["client_first_add"]["i"] == 0
    # the kernel twin: n 1 at age 6, booked at the landing age
    assert abs(x["kernel_delta"] - L.kernel_delta(K(), 1.0, 6.0, x["last_after"], False)[0]) < 1e-12


def test_the_climb_and_the_projection():
    k = K()
    p1 = G.projection(k, 1)
    assert p1[0]["add"] == 0.0 and abs(p1[4]["add"] - 9.978) < 1e-3
    steady = float(k.monotony.SLOPE) * (1.0 / (1.0 - 2.0 ** (-24.0 / 72.0)) - 1.0)
    assert abs(steady - 16.54) < 0.01
    assert 15.0 < p1[13]["add"] < steady and all(a["add"] < b["add"] for a, b in zip(p1, p1[1:]))
    p3 = G.projection(k, 3, hours=(8.0, 13.0, 20.0))
    assert p3[-1]["unhappy"] == 100.0
    eats = [{"food": L.MONO, "day": d, "label": "M%d" % d, "add": {"UNHAPPINESS": a}, "kernel_delta": a,
             "nominal_delta": a} for d, a in enumerate((0.0, 3.4, 6.1, 8.3, 10.0))]
    c = G.climb(eats, [], k)
    assert [r["running_sum"] for r in c["arms"]["mono"]][-1] == 27.8 and c["arms"]["staple"] == []
    f = G.fifth([dict(eats[-1], label="M4", add={"UNHAPPINESS": 9.99, "BOREDOM": 9.9}, nominal_delta=9.978)])
    assert f["M4"]["unhappy_within"] is True and f["M4"]["bored_within"] is False and f["S4"]["measured"] is False
