"""x34_monotony_lib and x34_grade (Plan 11f Task 9r): the floor-design chain's calendar, the replay's events (the
autodrop kind, the setany placement at or after the before-snapshot that shows the set value), the kernel twin, the
eat with no add, the reconnect, and the grade's row model, release, reconnect and oracle. Pure Python and the lupa
host: no game. Every loop runs on a fake clock (ruling T7-2)."""
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                          # testing/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x34_monotony_lib as L   # noqa: E402
import x34_grade as G          # noqa: E402
from pzt.session import Timeline   # noqa: E402


def K():
    return L._kh_static().K


# --- the calendar and the ring -------------------------------------------------------------------------------------

def test_the_calendar():
    monos = [(lab, age, food) for age, kind, lab, food in L.SCHEDULE if kind == "mono"]
    m = [x for x in monos if x[0].startswith("M")]
    v = [x for x in monos if x[0].startswith("V")]
    assert [x[1] for x in m[:5]] == [6.0, 12.0, 25.0, 30.0, 36.0]               # day 0 13:00, 19:00, day 1 08/13/19
    assert len(m) == 14 and all(x[2] == L.MONO for x in m)
    assert len(v) == 12 and len({x[2] for x in v}) == 12 and L.MONO not in {x[2] for x in v}
    assert all(f in L.PORTION_KCAL for f in L.VARIED)                             # each eaten once: n <= 1, level 0
    assert v[0][1] == L.at(5, 8.0) == 121.0
    rc = [x for x in L.SCHEDULE if x[1] == "reconnect"]
    assert len(rc) == 1 and rc[0][0] == L.at(5, 20.0) == 133.0
    resets = [x for x in L.SCHEDULE if x[1] == "refill" and x[3] is True]
    gaps = [b[0] - a[0] for a, b in zip(resets, resets[1:])]
    assert max(gaps) <= 6.5 + 1e-9                                              # change 4: at most 6.5 h apart
    ages = [x[0] for x in L.SCHEDULE]
    assert ages == sorted(ages)
    assert len([x for x in L.SCHEDULE if x[1] == "dayend"]) == 9


def test_the_ring():
    assert len(L.RING_RECORD) + len(L.RING_GLOBALS) <= 32
    for p in (L.MOOD_U, L.MOOD_B, L.PTARGET, L.DEHYD, L.UTARGET) + L.MONO_PATHS:
        assert p in L.RING_RECORD
    for p in (L.IN_PANIC, L.IN_STRESS, L.IN_UT, L.IN_BT, L.LANDED, L.EATS, L.WRITES):
        assert p in L.RING_GLOBALS
    assert L.STAT_NAMES["PANIC"] == "Panic" and L.STAT_NAMES["STRESS"] == "Stress"


# --- the replay's events -------------------------------------------------------------------------------------------

def test_autodrop_events_use_the_tool_kind():
    rows = [{"s": 1, "age": 1.0, L.AUTODROP: 0.0}, {"s": 2, "age": 1.02, L.AUTODROP: 0.1}]
    ev = L.autodrop_events(rows)
    assert ev == [{"s": 2, "kind": "autodrop", "g": 200.0, "label": "autodrop", "autoDrop": 0.1, "age": 1.02}]


def test_the_set_sits_at_the_first_row_at_or_after_the_before_snapshot_that_shows_it():
    rows = [{"s": 1, "age": 1.0, "BOREDOM": 30.0}, {"s": 2, "age": 1.02, "BOREDOM": 30.03},
            {"s": 3, "age": 1.04, "BOREDOM": 0.0}, {"s": 4, "age": 1.06, "BOREDOM": 0.42}]
    # the before-snapshot equal to row 2's age counts as at-or-after (F-T8-5), but row 2 does not show the set yet
    x = {"label": "R1", "stat": "BOREDOM", "value": 0.0, "before_age": 1.02, "after_age": 1.03, "ok": True}
    ev, notes = L.setany_events(rows, [x])
    assert not notes and ev[0]["s"] == 3 and ev[0]["kind"] == "stat"
    # a row at exactly the before-snapshot that shows it is chosen (>=)
    rows[1]["BOREDOM"] = 0.0
    assert L.setany_events(rows, [x])[0][0]["s"] == 2
    # nothing shows it within the quarter hour: the first row after the after-snapshot
    rows2 = [{"s": 1, "age": 1.0, "BOREDOM": 5.0}, {"s": 2, "age": 1.5, "BOREDOM": 5.0}]
    y = {"label": "R2", "stat": "BOREDOM", "value": 0.0, "before_age": 1.0, "after_age": 1.01, "ok": True}
    assert L.setany_events(rows2, [y])[0][0]["s"] == 2
    ev, notes = L.setany_events(rows2, [dict(y, ok=False)])
    assert ev == [] and notes


def test_the_kernel_target_is_the_kernels_level():
    k = K()
    m = k.monotony.new()
    for a in (6.0, 12.0, 25.0, 30.0):
        e = k.monotony.record(m, L.MONO, a, 1, False)
    for age in (30.0, 31.5, 60.0, 200.0):
        assert abs(L.kernel_target(k, e.n, e.last, age) - k.monotony.level(e, age)) < 1e-12
    assert L.kernel_target(k, None, 3.0, 4.0) == 0.0
    assert abs(L.kernel_target(k, 1.0 + 2 ** (-6 / 72.0), 12.0, 12.0) - 4.3 * 2 ** (-6 / 72.0)) < 1e-9


# --- the session verbs on fakes ------------------------------------------------------------------------------------

class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now

    def sleep(self, s):
        self.now += max(s, 0.01)


class FakeServer:
    """A server whose eat books the count and moves no stat (the floor design); the client copy follows one answer
    later. `online` answers the departure poll; each answer advances the world by one game minute."""
    def __init__(self, clock):
        self.clock = clock
        self.srv = {"BOREDOM": 12.0, "UNHAPPINESS": 14.0, "PANIC": 0.0, "STRESS": 0.0}
        self.cli = dict(self.srv)
        self.landed, self.mono, self.age = 5, 2, 30.0
        self.queued, self.polls = False, 0
        self.entries = {L.MONO: {"n": 2.0, "last": 25.0}}
        self.cmds = []
        self.online = True
        self.quit_after = None

    def answer(self, side, cmd, args):
        self.clock.now += 1.0
        self.age += 1.0 / 60
        self.cmds.append((side, cmd, args))
        cli_view = dict(self.cli)
        self.cli = dict(self.srv)
        if cmd == "eat.action":
            self.queued = True
            self.food = args.split()[0]
            return {"queued": True, "fraction": 1}
        if cmd == "stats.setany":
            _, stat, v = args.split()
            before = self.srv[stat]
            self.srv[stat] = float(v)
            return {"ok": True, "stat": stat, "before": before, "after": float(v)}
        if cmd == "stats.all":
            st = cli_view if side == "client" else self.srv
            return {"worldAge": self.age, "stats": {("Panic" if k == "PANIC" else "Stress" if k == "STRESS" else k): v
                                                     for k, v in st.items()} | {"HUNGER": 0.3}}
        if cmd == "lua.read":
            paths = args.split()[1:]
            if args.startswith("record:"):
                vals = {}
                for p in paths:
                    for f, e in self.entries.items():
                        for leaf in ("n", "last"):
                            if p == L.mono_path(f, leaf):
                                vals[p] = e[leaf]
                    if p == L.MOOD_U:
                        vals[p] = 14.0
                return {"ok": True, "values": vals}
            if L.FLUSH_PATHS[0] in paths:
                return {"ok": True, "values": ({L.FLUSH_PATHS[0]: "x"} if self.online else {})}
            if self.queued:
                self.polls += 1
                if self.polls == 3:
                    self.landed += 1
                    self.mono += 1
                    self.entries[self.food] = {"n": 2.9, "last": self.age} if self.food == L.MONO else \
                        {"n": 1.0, "last": self.age}
            vals = {"NutritionRevamp.server.intake.stats.eats": self.landed,
                    "NutritionRevamp.server.intake.stats.landed": self.landed,
                    "NutritionRevamp.server.intake.stats.monotony": self.mono,
                    L.WRITES[3:]: 100}
            return {"ok": True, "values": {p: vals.get(p, 0) for p in paths}}
        if cmd == "time.snapshot":
            return {"worldAge": self.age, "hour": 13, "minutes": 0, "mult": 1}
        if cmd == "foodtimer.set":
            return {"after": 0}
        return {"ok": True}


def fake_session(tmp_path, fake):
    S = object.__new__(L.Session)
    S.out = {"phase_walls": {}, "phase_errors": {}, "notes": [], "phases": {"X": {}}, "deviations": [], "steps": [],
             "verdicts": {}}
    S.tl, S.t0, S.cur = Timeline(), fake.clock.now, "X"
    S.path = str(tmp_path / "doc.json")
    S.run_dir = str(tmp_path)
    S.server, S.clients, S.started = None, {}, []
    S.stops, S.marks, S.speeds, S.eats, S.sets = [], [], [], [], []
    S.budget_s = 1e9
    S.rec_fx = {"name": "default"}
    S.prof = types.SimpleNamespace(safemode=False, launcher="java", client_timeout=180)

    def step(name, side, cmd, args="", timeout=30, log=True):
        w = S.wall()
        return {"step": name, "side": side, "cmd": cmd, "args": args, "phase": S.cur, "wall_before": w,
                "wall_after": w + 0.2, "took": 0.2, "ack": fake.answer(side, cmd, args)}
    S.step = step
    S.check = lambda: None
    S.one = lambda tag="one": {}
    S.fast = lambda tag="fast": {}
    S.spawn = lambda full, n=1, tag="spawn": {"add": {"ok": True}, "seen": {"resolved": "1"}}
    S.rcon = lambda cmd, tag: {"ok": True}
    return S


def patch_clock(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(L, "time", types.SimpleNamespace(time=clock.time, sleep=clock.sleep))
    monkeypatch.setattr(L, "POLL_S", 0.0)
    return clock


def test_an_eat_sets_nothing_and_brackets_the_landing(tmp_path, monkeypatch):
    fake = FakeServer(patch_clock(monkeypatch))
    S = fake_session(tmp_path, fake)
    st = S.mono_eat(L.MONO, "M1_1300", 30.0)
    assert st["landed"] is True and st["day"] == 1
    assert not [c for c in fake.cmds if c[1] == "stats.setany"]                   # change 2: no setany at an eat
    assert st["pre"]["UNHAPPINESS"] == 14.0 and st["post"]["UNHAPPINESS"] == 14.0
    assert st["pre"]["PANIC"] == 0.0 and st["post"]["STRESS"] == 0.0              # change 9 (F-T9-5)
    assert st["target_before"] is st["mono_before"] and st["mono_after"]["n"] == 2.9
    assert st["window_end_age"] >= st["landed_age_polled"] + L.WINDOW_M / 60.0 - 1e-9
    x = L.eat_reading(st, K())
    assert x["change"]["UNHAPPINESS"] == 0.0 and x["no_jump"]["UNHAPPINESS"] is True
    assert x["target_jump"] > 3.0 and x["client_seen"] is not None


def test_a_varied_eat_reads_mono450s_entry_for_the_target(tmp_path, monkeypatch):
    fake = FakeServer(patch_clock(monkeypatch))
    S = fake_session(tmp_path, fake)
    st = S.mono_eat("TKX.Mixed400", "V5_0800", 121.0)
    assert st["mono_before"]["n"] is None and st["mono_after"]["n"] == 1.0
    assert st["target_before"]["n"] == 2.0 and st["target_after"]["n"] == 2.0
    assert abs(L.eat_reading(st, K())["target_jump"]) < 1e-12


def test_a_reset_refill_sets_boredom_and_logs_the_set(tmp_path, monkeypatch):
    fake = FakeServer(patch_clock(monkeypatch))
    S = fake_session(tmp_path, fake)
    st = S.refill("R1_0400", 21.0, reset=True)
    assert ("server", "stats.setany", "admin BOREDOM 0.0") in fake.cmds
    assert st["reset"]["before"] == 12.0 and st["reset"]["after"] == 0.0
    assert S.sets == [st["reset"]] and S.sets[0]["before_age"] < S.sets[0]["after_age"]
    S.refill("R1_0100", 18.0)
    assert len(S.sets) == 1


def test_the_gate_reads_panic_then_zeroes_the_moods(tmp_path, monkeypatch):
    fake = FakeServer(patch_clock(monkeypatch))
    S = fake_session(tmp_path, fake)
    S.gate()
    G_ = S.out["phases"]["X"]["gate"]
    assert G_["server_before"]["UNHAPPINESS"] == 14.0 and G_["server_after"]["UNHAPPINESS"] == 0.0
    assert G_["server_after"]["BOREDOM"] == 0.0 and G_["server_before"]["PANIC"] == 0.0
    assert [x["stat"] for x in S.sets] == ["UNHAPPINESS", "BOREDOM"]
    assert not [c for c in fake.cmds if "panicTarget" in c[2] and c[1] != "lua.read"]


class FakeClient:
    def __init__(self, fake):
        self.fake, self.seen, self.alive = fake, {}, True

    def start(self):
        self.fake.online = True

    def wait_ready(self, timeout=None):
        return 12.5

    def quit(self):
        self.fake.online = False
        return 0


def test_the_reconnect_waits_away_then_joins_a_new_client(tmp_path, monkeypatch):
    fake = FakeServer(patch_clock(monkeypatch))
    S = fake_session(tmp_path, fake)
    c1 = FakeClient(fake)
    S.clients = {L.USER: c1}
    made = []

    def mk(run_dir, user, server, rec, **kw):
        made.append((run_dir, user, kw))
        return FakeClient(fake), True
    monkeypatch.setattr(L, "make_client", mk)
    S.persist = lambda: None
    st = S.reconnect("C5_2000", 133.0)
    assert st["departed"] is True and st["done"] is True
    assert st["away_h"] >= L.AWAY_H
    assert made and made[0][0].endswith("c1b") and made[0][2] == {"safemode": False, "launcher": "java"}
    assert S.clients[L.USER] is not c1 and S.started == [S.clients[L.USER]]
    assert st["after_series"] and st["after_series"][-1]["server"]["worldAge"] >= \
        st["join_snap"]["worldAge"] + L.RECON_MINUTES / 60.0 - 1e-9
    assert S.stops[-1]["label"] == "C5_2000_R"                                   # the refill after the join


# --- the grade -----------------------------------------------------------------------------------------------------

class SynthSess:
    """A session made by stepping the kernel's own floor the way the writer does (K.hybrid.floor per minute with the
    target composed from the record), sampled as the ring samples: row k before drain k."""
    def __init__(self, k, eats, start_age, minutes, u0=0.0, b0=0.0, mutate=None, offline=()):
        self.pre, self.events, self.doc = "x34s", [], {"stops": []}
        m = k.monotony.new()
        c = k.hybrid.defaults()
        rise_u, rise_b = float(c.moodRiseUnhappy) * 60, float(c.moodRiseBored) * 60
        u, b, lu, lb = u0, b0, 0.0, 0.0
        landed = 0
        ring = []
        ev = sorted(eats)
        i = 0
        prev_inp = (None, None)
        prev_t = start_age
        for j in range(minutes):
            age = start_age + j / 60.0
            e = m.t[L.MONO]
            row = {"s": j + 1, "ev": j + 1, "drained": j, "age": age, "dtM": 1.0, "on": j not in offline,
                   "UNHAPPINESS": u, "BOREDOM": b, L.MOOD_U: lu, L.MOOD_B: lb, L.SAT_T: prev_t,
                   L.MONO_PATHS[0]: e.n if e is not None else None, L.MONO_PATHS[1]: e.last if e is not None else None,
                   L.UTARGET: 0.0, L.IN_UT: prev_inp[0], L.IN_BT: prev_inp[1], L.IN_PANIC: 0.0, L.LANDED: landed}
            ring.append(row)
            while i < len(ev) and ev[i] <= age + 1e-9:
                k.monotony.record(m, L.MONO, ev[i], 1, False)
                landed += 1
                i += 1
            if j in offline:
                continue
            tu, tb = k.monotony.target(m, age)
            v, lu = G.floor_model(k, u, tu, lu, rise_u)
            u = v
            v, lb = G.floor_model(k, b, tb, lb, rise_b)
            b = v
            if mutate is not None:
                u = mutate(j, u)
            prev_inp = (float(tu), float(tb))
            prev_t = age
        for r in ring:
            if r[L.MONO_PATHS[0]] is None:
                r.pop(L.MONO_PATHS[0])
                r.pop(L.MONO_PATHS[1])
        self.ring = ring
        self.rows = [{"s": r["s"], "UNHAPPINESS": r["UNHAPPINESS"], "BOREDOM": r["BOREDOM"]} for r in ring]

    def marks(self):
        return {}

    def stops(self, kind):
        return []


def test_the_grade_reads_the_kernels_own_floor_as_exact():
    k = K()
    S = SynthSess(k, [6.0, 12.0, 25.0], 5.0, 26 * 60)
    rows = G.row_table(S, k)
    R = G.summarize_rows(rows, k)
    assert R["TWIN"]["graded"] > 1000 and R["TWIN"]["over"] == 0
    assert R["MODEL_U"]["over"] == 0 and R["MODEL_B"]["outside"] == 0
    assert R["TRACK_U"]["over"] == 0 and R["TRACK_B"]["under"] == 0
    assert abs(R["RISE_U_PER_H"]["median"] - 22.0) < 1e-6 and abs(R["RISE_B_PER_H"]["median"] - 25.0) < 1e-6
    assert R["BORED_MAX"]["ok"] is True


def test_the_grade_catches_a_jump_at_the_eat():
    k = K()
    land = 12.0
    jmin = int(round((land - 5.0) * 60))

    def mutate(j, u):
        return u + 4.0 if j == jmin else u
    S = SynthSess(k, [6.0, land], 5.0, 10 * 60, mutate=mutate)
    R = G.summarize_rows(G.row_table(S, k), k)
    assert R["MODEL_U"]["over"] >= 1


def test_the_release_bound_and_a_cliff():
    k = K()
    eats = [L.at(d, h) for d in range(5) for h in (8.0, 13.0, 19.0) if not (d == 0 and h < 13.0)]
    S = SynthSess(k, eats, 5.0, int((150 - 5) * 60))
    rows = G.row_table(S, k)
    mono = [{"food": L.MONO, "landed": True, "landed_age_polled": a} for a in eats]
    rel = G.release([S], rows, k, mono)
    assert rel["measured"] and rel["U"]["over"] == 0 and rel["B"]["over"] == 0
    assert abs(rel["U"]["fall_minus_twin"]) < k.hybrid.FLOOR_EPS + 1e-9
    big = rows[-100]
    big["U"] = big["U_prev"] - 1.0
    assert G.release([S], rows, k, mono)["U"]["over"] == 1


def test_the_oracle_matches_the_kernel_tests_table():
    k = K()
    rows = G.oracle_run(k, [(d * 24.0 + mm / 60.0, L.MONO) for d in range(5) for mm in G.MEALS_3_MIN], 0.0, 5 * 24.0)
    first = next(r[0] for r in rows if r[1] >= 30 - 1e-9)
    assert int(first // 24) == 3                                                  # day 3, as mono14 (test_kernel_monotony)
    assert max(r[1] for r in rows) == 30.0


def test_the_reconnect_grade_lands_on_the_twin():
    k = K()
    eats = [L.at(d, h) for d in range(5) for h in (8.0, 13.0, 19.0) if not (d == 0 and h < 13.0)]
    n = int((140 - 5) * 60)
    off = set(range(int((130 - 5) * 60), int((137 - 5) * 60)))
    S = SynthSess(k, eats, 5.0, n, offline=off)
    stop = {"kind": "reconnect", "label": "C5_2000", "done": True, "away_h": 7.0, "away_from_age": 130.0}
    S.stops = lambda kind: [stop] if kind == "reconnect" else []
    rc = G.reconnect([S], k)
    assert rc["offline_rows"] == len(off) and rc["landed_on_target"] is True
    assert rc["fall_while_away_twin"] > 1.0
