"""x37_fitness_lib and x37_grade (Plan 11h Task 4): the live run of graded Fitness billing. The ring (the wrapper's
record, its counters, exeFallbacks); the kernel's exercise table read through the lib; the replay's exercise type set
from the ring by the tool's setpath event, so a synthetic live ring made by the mod's own server replay bills each
type's MET and replays exactly, and the grade bites on a wrong type, a wrong bill and a stale record that bills; the
moodle pairs' grade (equal, lag inside the push gap, mismatch); a set on a fake server and clock (ended by its timer,
stopped, refused). Pure Python on the lupa host: no game."""
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
import x37_fitness_lib as L   # noqa: E402
import x37_grade as G   # noqa: E402
from pzt.session import Timeline   # noqa: E402

TABLE = {"squats": 3.0, "pushups": 3.8, "situp": 3.8, "burpees": 7.5, "barbellcurl": 3.5, "dumbbellpress": 3.5,
         "bicepscurl": 3.5}


# --- the ring and the table ------------------------------------------------------------------------------------------

def test_the_ring_reads_the_wrappers_record_and_the_fallbacks_within_the_cap():
    paths = list(L.RING_RECORD) + list(L.RING_GLOBALS)
    assert len(paths) == 32 == len(set(paths))
    assert L.EXETYPE.endswith("fitness.exeType.admin") and L.EXETYPE in L.RING_GLOBALS
    assert L.FALLBACKS.endswith("metabolism.stats.exeFallbacks") and L.FALLBACKS in L.RING_GLOBALS
    assert {L.MET, L.EPOC, L.EXK, L.TRAIL_EX} <= set(L.RING_RECORD) and L.OPTIONAL_BEFORE_EAT == (L.EPOC,)
    assert L.FIT_PATHS[0] == L.EXETYPE[3:] and len(L.FIT_PATHS) == 10


def test_the_lib_reads_the_kernels_exercise_table():
    assert set(L.EXERCISES) == set(TABLE)
    for name, met in TABLE.items():
        assert L.exercise_met(name) == (met, True)
    assert L.exercise_met("yoga") == (6.0, False) and L.fitness_met() == 6.0 and L.idle_met() == 1.3


def test_the_exetype_events_follow_the_ring_and_the_flag_only_arm_clears_off_the_flag():
    rows = [{"s": 1, "on": True}, {"s": 2, "on": True, "exe": True, L.EXETYPE: "squats"},
            {"s": 3, "on": True, "exe": True, L.EXETYPE: "squats"}, {"s": 4, "on": True, L.EXETYPE: "squats"},
            {"s": 5, "on": False}, {"s": 6, "on": True}]
    ev = L.exetype_events(rows)
    assert [(e["s"], e["value"]) for e in ev] == [(2, "squats"), (6, None)]
    assert all(e["kind"] == "setpath" and e["path"] == L.EXETYPE for e in ev)
    fo = L.exetype_events(rows, flag_only=True)
    assert [(e["s"], e["value"]) for e in fo] == [(2, "squats"), (4, None)]


# --- a synthetic live ring: the mod's own server replay ---------------------------------------------------------------

def start_record():
    with open(os.path.join(REPO, "testing", "artifacts", "x281-20261011-033356", "start.json"), encoding="utf-8") as fh:
        return json.load(fh)


SETS = [("squats", 20, 25), ("burpees", 40, 44), ("bicepscurl", 60, 63)]   # (type, first flagged s, last flagged s)
STALE_TO = {25: 30, 44: 47, 63: 63}                                       # the record outlives a set to this s


def synth_set_ring(n=90, sets=SETS, stale_to=STALE_TO):
    """(ring, start): ring rows as the harness samples them (row s before drain s, carrying the flag and the record the
    server held), their record values from the mod's own server replay of the same flag and type events."""
    start = start_record()
    t0 = start["rec"]["satiety"]["t"]
    clock = [{"s": i + 1, "age": t0 + (i + 1) / 60.0, "dtM": 1.0, "on": True, "ev": i + 1, "drained": i,
              "exe": False} for i in range(n)]                       # the harness writes the flag on every row
    for name, a, b in sets:
        for c in clock:
            if a <= c["s"] <= b:
                c["exe"] = True
            if a <= c["s"] <= stale_to[b]:
                c[L.EXETYPE] = name
    events = []
    for name, a, b in sets:
        events += [{"s": a, "kind": "activity", "exercising": True}, {"s": b + 1, "kind": "activity", "exercising": False}]
    events += L.exetype_events(clock)
    out = RL.replay_live(clock, sorted(events, key=lambda e: e["s"]), start, paths=list(L.RING_RECORD) + [L.EXETYPE],
                         sleep_allowed=False, ring_activity=False)[0]
    by = {r["s"]: r for r in out}
    ring = []
    for c in clock[1:]:
        r = {k: v for k, v in by[c["s"]].items() if k != L.EXETYPE}
        r.update(c)
        ring.append(r)
    return ring, start


def replay(ring, start, flag_only=False):
    ev = L.exetype_events(ring, flag_only=flag_only)
    return RL.replay_live(ring, ev, start, paths=list(L.RING_RECORD), sleep_allowed=False)[0]


def test_each_flagged_drain_bills_its_types_met_and_the_set_reads_it():
    ring, _ = synth_set_ring()
    for name, a, b in SETS:
        bills = L.billing_rows(ring, asked=name)
        mine = [x for x in bills if a <= x["s"] <= b]
        assert len(mine) == b - a + 1 and all(x["ok"] and x["ok_asked"] and x["billed"] == TABLE[name] for x in mine)
        st = {"label": name, "exercise": name, "age_queued": ring[a - 3]["age"], "clear_age": ring[b]["age"],
              "record_during": name}
        x = L.set_reading(ring, st, rest_m=3.0)
        assert x["types_on_flagged"] == [name] and x["flag_runs"] == 1 and x["billed_asked_ok"] == b - a + 1
        assert x["stale_rows"] == min(STALE_TO[b], ring[b]["s"] + 3) - b
        assert x["stale_billed_type_met"] == 0                          # a stale record never bills
    before = next(r for r in ring if r["s"] == 19)
    assert before[L.MET] == 1.3                                          # the drain before the set bills idle


def test_the_replay_with_the_rings_type_reproduces_the_bill_and_the_flag_only_arm_agrees():
    ring, start = synth_set_ring()
    rep = replay(ring, start)
    m = L.met_agreement(ring, rep)
    assert m["ok"] and m["n"] > 80
    fo = replay(ring, start, flag_only=True)
    sets = [{"label": n, "exercise": n, "age_queued": ring[a - 3]["age"], "clear_age": ring[b]["age"],
             "record_during": n, "started": True, "ended": True} for n, a, b in SETS]
    gs = L.grade_sets(sets, ring, rep, fo)
    assert gs["met_live_vs_replay"]["ok"] and gs["met_live_vs_flag_only"]["ok"]
    assert gs["stale_rows_vs_flag_only"]["ok"] and gs["stale_rows_vs_flag_only"]["n"] >= 5
    assert all(x["record_ok"] and x["billed_all"] and x["fallbacks_ok"] for x in gs["sets"])
    assert L.diff_floor(rep, ring, L.TOL_GRADE)["ok"]


def test_the_grade_bites_on_a_wrong_type_a_wrong_bill_and_no_type():
    ring, start = synth_set_ring()
    bad = [dict(r) for r in ring]
    for r in bad:
        if r.get(L.EXETYPE) == "squats":
            r[L.EXETYPE] = "burpees"                                    # the record says burpees, the bill squats
    st = {"label": "s", "exercise": "squats", "age_queued": ring[17]["age"], "clear_age": ring[25]["age"],
          "record_during": "squats"}
    x = L.set_reading(bad, st)
    assert x["types_on_flagged"] == ["burpees"] and x["billed_ok"] == 0
    assert L.met_agreement(bad, replay(bad, start))["ok"] is False        # the replay bills the ring's burpees
    moved = [dict(r) for r in ring]
    moved[22][L.MET] = 6.0                                               # one drain billed the flat class
    assert L.met_agreement(moved, replay(ring, start))["mismatches"] == 1
    gs = L.grade_sets([dict(st, started=True, ended=True)], moved, None)
    assert gs["sets"][0]["billed_all"] is False and gs["sets"][0]["billed_ok_verdict"] is True   # one edge allowed
    none = [{k: v for k, v in r.items() if k != L.EXETYPE} for r in ring]
    rep = replay(none, start)
    assert {q[L.MET] for q in rep if 21 <= q["s"] <= 26} == {6.0}          # no record: the flat Fitness class
    stale = [dict(r) for r in ring]
    for r in stale:                                                      # a stale record that bills: the live bill
        if 26 <= r["s"] <= 30:                                           # after the set reads squats' 3.0
            r[L.MET] = 3.0
    fo = replay(ring, start, flag_only=True)
    sets = [dict(st, started=True, ended=True)]
    assert L.grade_sets(sets, stale, None, fo)["stale_rows_vs_flag_only"]["ok"] is False


def test_the_fallback_counter_rises_on_a_set_with_no_type():
    ring, start = synth_set_ring()
    none = [{k: v for k, v in r.items() if k != L.EXETYPE} for r in ring]
    be = RL.replay_live(none, [], start, paths=list(L.RING_RECORD) + [L.FALLBACKS], sleep_allowed=False)[0]
    f = [q.get(L.FALLBACKS) for q in be]
    assert f[-1] - f[0] == sum(b - a + 1 for _, a, b in SETS)
    be2 = RL.replay_live(ring, L.exetype_events(ring), start, paths=[L.FALLBACKS], sleep_allowed=False)[0]
    assert be2[-1][L.FALLBACKS] == be2[0][L.FALLBACKS]


# --- the moodle pairs -------------------------------------------------------------------------------------------------

def pair(tag, sig, levels, cw, sw=None):
    return {"tag": tag, "server_sig": sig, "client_levels": levels, "client_wall": cw,
            "server_wall": cw + 0.2 if sw is None else sw, "wall_gap": 0.2}


def test_the_moodle_pairs_read_each_signature_digit_and_allow_the_push_gap():
    z = {c: 0 for c in L.NR_CLASSES}
    assert L.sig_digit(12345, "overfull") == 1 and L.sig_digit(12345, "energy") == 2
    assert L.sig_digit(12345, "hydration") == 3 and L.sig_digit(12345, "stimulant") == 4
    assert L.sig_digit(12345, "sleep") == 5 and L.sig_digit(None, "sleep") is None
    ps = [pair("a", 10000, dict(z, overfull=1), 0.0), pair("b", 10100, dict(z, overfull=1), 30.0),
          pair("c", 10100, dict(z, overfull=1, hydration=1), 70.0)]
    gr = L.moodle_pairs_grade(ps)
    assert gr["ok"] and gr["classes"]["hydration"]["lag"] == 1 and gr["mismatch"] == 0
    late = ps[:2] + [pair("c", 10100, dict(z, overfull=1), 120.0)]       # still the old class 90 s after the change
    assert L.moodle_pairs_grade(late)["ok"] is False
    wide = [dict(ps[0], wall_gap=1.5)]
    assert L.moodle_pairs_grade(wide)["ok"] is False


def test_the_vanilla_pairs_count_equal_and_differing_moodles():
    ps = [{"tag": "a", "client_moodles": {"endurance": 1, "hungry": 0}, "server_moodles": {"endurance": 1, "hungry": 1},
           "client_body": {"hunger": 0.1, "endurance": 0.9}, "server_body": {"hunger": 0.1005, "endurance": 0.88},
           "stats_wall_gap": 0.3}]
    v = L.vanilla_pairs_reading(ps)
    assert v["moodles"]["endurance"]["equal"] == 1 and v["moodles"]["hungry"]["differ"] == 1
    assert abs(v["hunger_max_abs"] - 0.0005) < 1e-12 and abs(v["endurance_max_abs"] - 0.02) < 1e-12


# --- a set on a fake server and clock ---------------------------------------------------------------------------------

class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now

    def sleep(self, s):
        self.now += max(s, 0.01)


class FakeServer:
    """Each answer advances the world 0.25 game minutes. A set asked at age q shows the flag from q + 0.5 min and the
    record from its first showing; it clears at q + 0.5 + run_m (the timer), or one answer after player.stop; the record
    is cleared at a stop when clear_on_stop, and outlives a timer end when stale."""

    def __init__(self, clock, age=6.0, run_m=4.0, stale=True, refuse=False):
        self.clock, self.age = clock, age
        self.run_m, self.stale, self.refuse = run_m, stale, refuse
        self.q = None
        self.on = False
        self.rec = None
        self.starts = self.stops = 0
        self.stop_at = None
        self.cmds = []

    def tick(self):
        self.age += 0.25 / 60
        if self.q is not None and not self.refuse:
            t0 = self.q + 0.5 / 60
            end = t0 + self.run_m / 60 if self.stop_at is None else self.stop_at
            was = self.on
            self.on = t0 <= self.age < end
            if self.on and not was:
                self.rec, self.starts = self.name, self.starts + 1
            if was and not self.on:
                if self.stop_at is not None or not self.stale:
                    self.rec, self.stops = None, self.stops + 1
                self.q = None

    def answer(self, side, cmd, args):
        self.clock.now += 0.2
        self.tick()
        self.cmds.append((side, cmd, args))
        if cmd == "exercise.do":
            self.name = args.split()[0]
            self.q, self.stop_at = self.age, None
            return {"ok": True, "queued": True, "queueLen": 1}
        if cmd == "player.stop":
            if self.on:
                self.stop_at = self.age + 0.1 / 60
            return {"cleared": True}
        if cmd == "player.walk":
            return {"queued": True}
        if cmd == "witness.chain":
            if args.endswith("getCurrentExe"):
                return {"ok": True, "value": "zombie.characters.Fitness$FitnessExercise@1" if self.on else "nil"}
            return {"ok": True, "value": 6.0}
        if cmd == "time.snapshot":
            return {"worldAge": self.age, "hour": 13, "minutes": 0, "mult": 1}
        if cmd == "stats.get":
            return {"moodles": {"endurance": 0, "hungry": 0}, "hunger": 0.1, "endurance": 1.0, "worldAge": self.age}
        if cmd == "lua.read":
            paths = args.split()[1:]
            v = {L.FIT_PATHS[0]: self.rec, L.FIT_PATHS[1]: self.starts, L.FIT_PATHS[2]: self.stops,
                 L.FIT_PATHS[3]: 0, L.FIT_PATHS[4]: 0, L.FIT_PATHS[5]: 0, L.FIT_PATHS[6]: 0, L.FIT_PATHS[7]: True,
                 L.FIT_PATHS[8]: True, L.SRV_SIG[0]: 0, L.SRV_SIG[1]: 1, L.MET: 3.0}
            for p in L.CLI_MOODLES:
                v[p] = 0
            return {"ok": True, "values": {p: v.get(p) for p in paths if v.get(p) is not None}}
        return {"ok": True}


def fake_session(tmp_path, fake):
    S = object.__new__(L.Session)
    S.out = {"phase_walls": {}, "phase_errors": {}, "notes": [], "phases": {"X": {}}, "deviations": [], "steps": [],
             "verdicts": {}, "readings": {}}
    S.tl, S.t0, S.cur = Timeline(), fake.clock.now, "X"
    S.path = str(tmp_path / "doc.json")
    S.run_dir = str(tmp_path)
    S.server, S.clients, S.started = None, {}, []
    S.stops, S.marks, S.speeds, S.eats, S.drinks, S.pairs = [], [], [], [], [], []
    S.mpairs, S.sets, S.rests = [], [], []
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


def test_a_set_ended_by_its_timer_reads_the_record_during_and_the_stale_record_after(tmp_path, monkeypatch):
    fake = FakeServer(patch_clock(monkeypatch))
    S = fake_session(tmp_path, fake)
    st = S.run_set("squats", 3, "T1")
    assert st["started"] and st["ended"] and not st["stopped"] and st["record_during"] == "squats"
    assert st["at_clear"]["exeType"] == "squats" and st["after_rest"]["exeType"] == "squats"     # stale, named
    e = L.end_case(st)
    assert e["how"] == "timer" and e["record_after_rest"] == "squats" and e["stops_delta_after_rest"] == 0
    assert abs(e["ran_min"] - 4.0) < 0.6 and st["after_rest"]["age"] >= st["clear_age"] + L.REST_M / 60 - 1e-9
    assert [p["tag"] for p in S.mpairs] == ["T1_mid", "T1_end"]
    assert not any(c[1] == "player.stop" for c in fake.cmds)


def test_a_stopped_set_cancels_walks_and_reads_the_cleared_record(tmp_path, monkeypatch):
    fake = FakeServer(patch_clock(monkeypatch), run_m=20.0)
    S = fake_session(tmp_path, fake)
    st = S.run_set("pushups", 20, "M1", stop_after_m=2.0)
    assert st["stopped"] and st["ended"] and st["walk"]["queued"] is True
    e = L.end_case(st)
    assert e["how"] == "stopped" and e["record_at_clear"] is None and e["stops_delta_at_clear"] == 1
    assert 2.0 <= e["ran_min"] < 5.0                                    # a fake poll spans about 2 game minutes
    names = [c[1] for c in fake.cmds]
    assert names.index("player.walk") > names.index("player.stop") and names.count("player.stop") == 2


def test_a_refused_set_is_named_and_reads_nothing_more(tmp_path, monkeypatch):
    fake = FakeServer(patch_clock(monkeypatch), refuse=True)
    S = fake_session(tmp_path, fake)
    st = S.run_set("burpees", 3, "R1")
    assert st["started"] is False and L.end_case(st)["how"] == "refused" and "at_clear" not in st
    assert any("never showed" in n["note"] for n in S.out["notes"])


def test_the_grade_names_both_sessions():
    assert G.DOCS == {"x371": "fitness-1.json", "x372": "fitness-2.json"}


# --- the drivers' grades on the synthetic ring -------------------------------------------------------------------------

import x371_fitness as D1   # noqa: E402
import x372_fitness as D2   # noqa: E402


def driver_state(sets_spec, how):
    ring, start = synth_set_ring(sets=sets_spec, stale_to={b: b if h == "stopped" else b + 3
                                                           for (_, _, b), h in zip(sets_spec, how)})
    rep, fo = replay(ring, start), replay(ring, start, flag_only=True)
    sets = []
    for (n, a, b), h in zip(sets_spec, how):
        st = {"label": n, "exercise": n, "age_queued": ring[a - 3]["age"], "clear_age": ring[b]["age"],
              "first_on_age": ring[a - 1]["age"], "record_during": n, "started": True, "ended": True,
              "stopped": h == "stopped", "before": {"stops": 0, "starts": 0, "fallbacks": 0},
              "at_clear": {"stops": 1 if h == "stopped" else 0, "exeType": None if h == "stopped" else n},
              "after_rest": {"stops": 1 if h == "stopped" else 0, "exeType": None if h == "stopped" else n,
                             "fallbacks": 0}}
        sets.append(st)
    z = {c: 0 for c in L.NR_CLASSES}
    S = types.SimpleNamespace(out={"readings": {}, "verdicts": {}}, sets=sets,
                              mpairs=[pair("a", 0, z, 0.0), pair("b", 0, z, 10.0)])
    return S, ring, rep, fo


def test_the_drivers_grade_their_sets_on_a_synthetic_ring():
    assert D1.SETS + D2.SETS == L.EXERCISES[:4] + L.EXERCISES[4:] and D1.STOP is None and D2.STOP[0] == "squats"
    assert D1.ARTIFACT == G.DOCS["x371"] and D2.ARTIFACT == G.DOCS["x372"] and D1.PROFILE == D2.PROFILE == "x37-fitness"
    spec = [(n, 10 + 12 * i, 14 + 12 * i) for i, n in enumerate(D1.SETS)]
    S, ring, rep, fo = driver_state(spec, ["timer"] * 4)
    D1.grade(S, ring, rep, fo)
    v = {k: x["verdict"] for k, x in S.out["verdicts"].items()}
    assert all(x == "as_predicted" for x in v.values()), v
    spec = [(n, 10 + 12 * i, 14 + 12 * i) for i, n in enumerate(D2.SETS + ("squats",))]
    S, ring, rep, fo = driver_state(spec, ["timer"] * 3 + ["stopped"])
    D2.grade(S, ring, rep, fo)
    v = {k: x["verdict"] for k, x in S.out["verdicts"].items()}
    assert all(x == "as_predicted" for x in v.values()) and "END_MOVE" in v, v
    S.sets[-1]["at_clear"]["exeType"] = "squats"                         # the cancel left the record: falsified
    D2.grade(S, ring, rep, fo)
    assert S.out["verdicts"]["END_MOVE"]["verdict"] == "falsified"
