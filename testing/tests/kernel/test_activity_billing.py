"""Plan 11f C-17 (option C, Angus 2026-10-11; ruling C17-1): exercise is billed by the activity, plus an after-burn pool.

The engine moves its metabolic rate toward the activity's target as an asymmetric first-order lag (rising 0.001 and
falling 0.0004 of the gap per update, times GameTime's multiplier: 09-post-exercise-tail.md section 1b), measured live at
DayLength 1 as tau_rise 0.558-0.562 h and tau_fall 1.346-1.380 h (section 2a). The mod billed that lagged rate: a 1 h
Fitness set under-billed its rise and billed about 450 kcal of tail as exercise (x29-lag; 445-469 kcal on the clean
bouts). Now (K.energy.billClass, K.energy.epoc, NR_Server_Metabolism MET.readBilled and MET.spend):

- while the server's exercise flag is set (getCurrentExe, #2901) the minute bills the Fitness class (6.0 with no
  recorded exercise type, as here; the recorded type's own MET since Plan 11h, test_exercise_grading.py);
- while the load-stripped rate falls with no exercise and no movement, the idle class (Default, 1.3);
- otherwise the rate's own class (every other activity keeps the engine's lag);
- each flagged minute adds EPOC_F of its exercise kcal to body.epoc, laid lazily, released with EPOC_TAU_H as
  expenditure, never as exercise kcal (exKcalDay, the window's ex and the lag L do not see it).

The bout oracles drive the server path (tools/replay_live.py's ServerReplay: the mod's own adapters) with the engine's
lag reproduced minute by minute from the measured constants, so the old rule's tail on the same inputs is a reading
beside the new one. The ring parity test runs a stand-in live server with the harness's ring (3daaca9: rows carry the raw
engine `rate` and the exercise flag `exe`) and replays it with the activity taken from those exogenous fields, never
from body.met, which it grades.
"""
import json
import math
import os
import sys

import pytest

from .server_host import REPO
from .test_harness_minute_ring import CORE, SERVER, STUB_TK, load, section
from .test_metabolism_shape import MET, fresh, met_host, minute, player  # noqa: F401  (met_host is a fixture)

sys.path.insert(0, os.path.join(REPO, "tools"))
import replay_live as RL  # noqa: E402

TAU_RISE_MIN = 0.558 * 60          # the measured rise toward Fitness 6.0 (x292 B0), game minutes at DayLength 1
TAU_FALL_MIN = 1.36 * 60           # the measured fall toward 1.5 (x292-x296, 1.346-1.380 h)
IDLE_RATE = 1.5                    # the engine's Default class, a standing player's asymptote
LIVE_TAIL_KCAL = 445.0             # the smallest clean live tail after a 1 h set (x296 B6, 444.9; 09 section 2b)
W = 80.0


# --- the kernel ------------------------------------------------------------------------------------------------------

def test_the_constants_and_their_labels(host):
    E = host.K.energy
    assert E.EPOC_F == 0.10 and E.EPOC_TAU_H == 0.5 and E.FALL_EPS == 1e-4
    path = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Kernel_Energy.lua")
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    f_line = next(x for x in src.splitlines() if x.startswith("K.energy.EPOC_F = "))
    tau_line = next(x for x in src.splitlines() if x.startswith("K.energy.EPOC_TAU_H = "))
    assert "game choice" in f_line and all(s in f_line for s in ("S1775", "S1777", "S1779", "S1783"))
    assert "denominators differ" in f_line
    assert "game choice" in tau_line and "S1798 stays open" in tau_line
    assert all(s in tau_line for s in ("S1796", "S1797", "S1790", "S1791", "S1777", "S1783"))
    assert "game choice" in next(x for x in src.splitlines() if x.startswith("K.energy.FALL_EPS = "))


@pytest.mark.parametrize("prev,rate,falls", [(2.0, 1.9, True), (1.5, 1.5, False), (1.5, 1.6, False),
                                             (1.5, 1.5 - 0.5e-4, False), (1.5, 1.5 - 2e-4, True),
                                             (None, 1.5, False), (1.5, None, False),
                                             (float("nan"), 1.0, False), (2.0, float("nan"), False)])
def test_rate_falling(host, prev, rate, falls):
    assert host.K.energy.rateFalling(prev, rate) is falls


@pytest.mark.parametrize("cls,exe,moving,falling,bill", [
    ("Walking5kmh", True, False, False, "Fitness"),       # the flag bills Fitness whatever the rate reads
    ("Default", True, False, True, "Fitness"),            # from the first minute, before the rate has risen
    ("HeavyWork", True, True, False, "Fitness"),
    ("Sleeping", True, False, True, "Sleeping"),          # asleep wins
    ("UsingTools", False, False, True, "Default"),        # a falling tail bills idle
    ("LightDomestic", False, False, True, "Default"),
    ("UsingTools", False, True, True, "UsingTools"),      # moving keeps the rate's class at or below Walking5kmh
    ("DefaultExercise", False, True, True, "DefaultExercise"),
    ("Walking5kmh", False, True, True, "Walking5kmh"),
    ("Running10kmh", False, True, True, "Walking5kmh"),   # a moving fall above Walking5kmh is capped (ruling C17-5)
    ("HeavyWork", False, True, True, "Walking5kmh"),
    ("Running10kmh", False, True, False, "Running10kmh"), # a steady or rising moving rate keeps its class
    ("Sleeping", False, True, True, "Sleeping"),
    ("UsingTools", False, False, False, "UsingTools"),    # a steady or rising rate keeps its class
    ("SeatedResting", False, False, True, "SeatedResting"),   # the gate never raises a bill
    ("StandingAtRest", False, False, True, "StandingAtRest"),
    ("Unknown", False, False, True, "Unknown"),           # an unknown class bills 1.3 already
])
def test_bill_class(host, cls, exe, moving, falling, bill):
    assert host.K.energy.billClass(cls, exe, moving, falling) == bill


def _body(host):
    b = host.table(dict(lm=65.6, fm=14.4, at=0.0, inDay=0.0, eeDay=0.0, ebDay=0.0, actKcalDay=0.0, exKcalDay=0.0))
    b.trail = host.K.body.newTrail(0.5)
    return b


def test_no_exercise_lays_no_pool(host):
    b = _body(host)
    rel, healed = host.K.energy.epoc(b, False, 40.0, 1.0)
    assert rel == 0 and healed is False and b.epoc is None and b.eeDay == 0
    rel, healed = host.K.energy.epoc(b, True, 0.0, 1.0)        # flagged, but no exercise kcal: nothing to bank
    assert rel == 0 and b.epoc is None


def test_a_flagged_minute_banks_f_and_releases_on_tau(host):
    E = host.K.energy
    b = _body(host)
    rel, healed = E.epoc(b, True, 50.0, 1.0)
    k = math.exp(-1.0 / 30.0)
    assert rel == pytest.approx(5.0 * (1 - k), rel=1e-12) and healed is False
    assert b.epoc == pytest.approx(5.0 * k, rel=1e-12)
    assert b.eeDay == pytest.approx(rel, rel=1e-12) and b.ebDay == pytest.approx(-rel, rel=1e-12)
    assert host.K.body.trail24(b.trail, "ee") == pytest.approx(rel, rel=1e-12)
    assert b.exKcalDay == 0 and host.K.body.trail24(b.trail, "ex") == 0   # never exercise kcal
    pool = b.epoc
    rel2, _ = E.epoc(b, False, 50.0, 2.0)                   # unflagged: releases only
    assert rel2 == pytest.approx(pool * (1 - math.exp(-2.0 / 30.0)), rel=1e-12)
    rel3, _ = E.epoc(b, False, 0.0, 0.0)                    # no time, no release
    assert rel3 == 0


def test_a_bad_pool_or_input_heals(host):
    E = host.K.energy
    for bad in (float("nan"), float("inf"), -3.0, "x", True):
        b = _body(host)
        b.epoc = bad
        rel, healed = E.epoc(b, False, 0.0, 1.0)
        assert healed is True and rel == 0 and b.epoc is None   # healed to 0, which is under the floor: pruned
    b = _body(host)
    for bad in (float("nan"), -5.0):
        rel, healed = E.epoc(b, True, bad, 1.0)
        assert rel == 0 and healed is False and b.epoc is None


# --- the adapter -----------------------------------------------------------------------------------------------------

def _reset(h):
    MET(h).prevRate = h.rt.table()
    MET(h).prevExe = h.rt.table()


def test_the_minute_the_flag_clears_bills_idle_even_on_a_rising_rate(met_host):
    h = met_host
    _reset(h)
    p = player(h, rate=4.0, exe="squats", moving=False)
    record = fresh(h, p)
    p.cfg.exe = None
    p.cfg.rate = 4.5                                      # the drain read the rate's last rise
    minute(h, p, record, 100.0 + 1 / 60)
    assert record["body"]["met"] == 1.3
    p.cfg.rate = 5.0                                      # a rise with no flag: the rate's class again
    minute(h, p, record, 100.0 + 2 / 60)
    assert record["body"]["met"] == 5.0                   # DiggingSpade, billed 5.0


def test_a_flagged_minute_bills_fitness_and_lays_the_pool(met_host):
    h = met_host
    _reset(h)
    p = player(h, rate=1.6, exe="squats", moving=False)
    record = fresh(h, p)
    pipe = h.rt.table()
    minute(h, p, record, 100.0 + 1 / 60, pipe)
    body = record["body"]
    assert body["met"] == 6.0 and pipe["activityClass"] == "Fitness" and pipe["exercising"] is True
    assert body["epoc"] > 0


def test_the_training_sample_banks_the_rates_engine_class_not_the_bill(met_host):
    h = met_host
    _reset(h)
    p = player(h, rate=3.1, exe="squats", moving=False)
    record = fresh(h, p)
    body = record["body"]
    m0 = body["metMinDay"]
    minute(h, p, record, 100.0 + 1 / 60)
    w = body["fm"] + body["lm"]
    assert body["met"] == 6.0
    assert body["metMinDay"] - m0 == pytest.approx((3.1 - 1.5) * w / 80, rel=1e-9)   # Walking5kmh's engine 3.1


def test_a_falling_rate_standing_bills_idle_and_moving_keeps_its_class(met_host):
    h = met_host
    for moving, bill in ((False, 1.3), (True, 3.0)):
        _reset(h)
        p = player(h, rate=4.0, moving=moving)
        record = fresh(h, p)
        p.cfg.rate = 3.0                                  # DefaultExercise, falling
        pipe = h.rt.table()
        minute(h, p, record, 100.0 + 1 / 60, pipe)
        assert record["body"]["met"] == bill
        assert pipe["activityClass"] == ("Default" if bill == 1.3 else "DefaultExercise")
        assert record["body"]["epoc"] is None             # no exercise, no pool
        p.cfg.rate = 3.0                                  # steady: the class again
        minute(h, p, record, 100.0 + 2 / 60)
        assert record["body"]["met"] == 3.0


def test_the_first_minute_after_a_boot_reads_no_fall(met_host):
    h = met_host
    _reset(h)
    p = player(h, rate=4.0, moving=False)
    record = fresh(h, p)
    _reset(h)                                             # the held rate is memory only
    p.cfg.rate = 3.0
    minute(h, p, record, 100.0 + 1 / 60)
    assert record["body"]["met"] == 3.0


def test_the_fall_reads_the_raw_rate_so_a_load_drop_at_a_steady_class_bills_one_idle_minute(met_host):
    # Plan 11f ruling C26-1: both minutes compare on the raw engine rate. A carried load that drops between minutes
    # lowers the raw rate while the stripped one holds; the raw fall reads as a fall (the accepted cost: one idle
    # minute for a still player at a sustained class who drops weight)
    h = met_host
    _reset(h)
    loaded = 3.1 * (1 + 0.35 * 0.5 * 0.5)
    p = player(h, rate=loaded, carried=10.0, maxW=20, moving=False)
    record = fresh(h, p)
    p.cfg.rate = 3.1
    p.cfg.carried = 0.0
    minute(h, p, record, 100.0 + 1 / 60)
    assert record["body"]["met"] == 1.3
    minute(h, p, record, 100.0 + 2 / 60)                  # steady at 3.1: the class again
    assert record["body"]["met"] == 3.8


def test_the_pools_release_never_reaches_the_lag(met_host):
    h = met_host
    _reset(h)
    p = player(h, rate=1.5, exe="squats", moving=False)
    record = fresh(h, p)
    minute(h, p, record, 100.0 + 1 / 60)
    body = record["body"]
    assert body["epoc"] > 0
    p.cfg.exe = None
    L0 = record["satiety"]["L"]
    ex0, ee0 = body["exKcalDay"], body["eeDay"]
    minute(h, p, record, 100.0 + 2 / 60)
    assert body["exKcalDay"] == ex0                       # the idle minute: no exercise kcal
    assert record["satiety"]["L"] == pytest.approx(h.K.deficit.exerciseLag(L0, 0, 1 / 60), rel=1e-12)
    w = body["fm"] + body["lm"]
    rest = h.K.energy.ree(body["lm"]) / 1440 * (1 - body["at"]) + (1.3 - 1.0) * w / 60
    assert body["eeDay"] - ee0 > rest                     # the release is billed as expenditure


def test_a_bad_pool_heals_and_counts(met_host):
    h = met_host
    _reset(h)
    p = player(h, rate=1.5, moving=False)
    record = fresh(h, p)
    record["body"]["epoc"] = float("nan")
    g0 = MET(h).guarded
    minute(h, p, record, 100.0 + 1 / 60)
    assert record["body"]["epoc"] is None and MET(h).guarded == g0 + 1   # healed to 0, then pruned


def test_a_steady_walker_never_carries_a_pool(met_host):
    h = met_host
    _reset(h)
    p = player(h, rate=6.0, moving=True)
    record = fresh(h, p)
    for i in range(1, 30):
        minute(h, p, record, 100.0 + i / 60)
    assert record["body"]["epoc"] is None and record["body"]["met"] == 6.0


def test_the_limitations_name_the_flag_the_gate_and_the_pool(met_host):
    lim = list(MET(met_host).limitations.values())
    assert any(x.startswith("every Fitness exercise bills its type's Compendium MET") and "bills the flat Fitness class "
               "(6.0), counted in stats.exeFallbacks" in x for x in lim)
    assert any("falling with no exercise and no movement bills the idle class" in x for x in lim)
    assert any(x.startswith("the after-burn follows the exercise flag") for x in lim)


def test_the_store_keeps_the_pool():
    from .server_host import Host
    h = Host()
    assert "body.epoc" in list(h.K.store.INPUTS.values())


# --- the server path: one Fitness bout with the engine's lag -----------------------------------------------------

def engine_rates(minutes, bout):
    """The engine's rate each game minute: from IDLE_RATE toward 6.0 over the bout (start, end) with TAU_RISE_MIN, then
    back toward IDLE_RATE with TAU_FALL_MIN (the jar's first-order lag at DayLength 1's measured constants)."""
    r, out = IDLE_RATE, []
    for m in range(minutes):
        out.append(r)
        if bout[0] <= m < bout[1]:
            r += (6.0 - r) * (1 - math.exp(-1 / TAU_RISE_MIN))
        else:
            r += (IDLE_RATE - r) * (1 - math.exp(-1 / TAU_FALL_MIN))
    return out


BOUT = (60, 120)
MINUTES = 60 + 60 + 12 * 60
PATHS = ("body.met", "body.exKcalDay", "body.eeDay", "body.epoc", "body.fm", "body.lm", "satiety.L")


def bout_run(exercise=True):
    rates = engine_rates(MINUTES, BOUT) if exercise else [IDLE_RATE] * MINUTES
    ev = []
    for m, r in enumerate(rates):
        e = {"minute": m, "kind": "activity", "rate": r}
        if m == BOUT[0] or m == BOUT[1]:
            e["exercising"] = exercise and m == BOUT[0]
        ev.append(e)
    rows, be = RL.replay_arm(ev, minutes=MINUTES, backend="server", start_age=8.0, paths=PATHS,
                             player={"weight": W, "female": False}, rng="half")
    return rows, be, rates


@pytest.fixture(scope="module")
def bout():
    return bout_run(True), bout_run(False)


def _net(rows, be):
    w = rows[BOUT[0]]["body.fm"] + rows[BOUT[0]]["body.lm"]
    return (be.K.energy.COMPENDIUM.Fitness - be.K.energy.COMPENDIUM.Default) * w / 60 * (BOUT[1] - BOUT[0]), w


def test_the_bout_bills_its_class_from_the_first_minute(bout):
    (rows, be, rates), _ = bout
    assert rates[BOUT[0]] == pytest.approx(IDLE_RATE)     # the engine has not risen yet
    assert [rows[m]["body.met"] for m in range(BOUT[0], BOUT[1])] == [6.0] * (BOUT[1] - BOUT[0])
    assert rows[BOUT[0] - 1]["body.met"] == 1.3


def test_the_bouts_exercise_kcal_are_the_class_net_cost(bout):
    (rows, be, _), _ = bout
    net, _ = _net(rows, be)
    ex = rows[BOUT[1] - 1]["body.exKcalDay"] - rows[BOUT[0] - 1]["body.exKcalDay"]
    assert ex == pytest.approx(net, rel=1e-9)
    assert rows[-1]["body.exKcalDay"] == rows[BOUT[1] - 1]["body.exKcalDay"]   # no tail billed as exercise


def test_billing_returns_to_idle_on_the_first_falling_minute(bout):
    (rows, be, rates), _ = bout
    assert rates[BOUT[1]] > rates[BOUT[1] - 1]            # the drain after the clear reads the rate's last rise:
    assert rates[BOUT[1] + 1] < rates[BOUT[1]]            # the flag's clear bills idle, then the fall does
    assert all(rows[m]["body.met"] == 1.3 for m in range(BOUT[1], MINUTES))


def test_a_decayed_pool_leaves_the_record_and_a_later_set_lays_it_again(host):
    E = host.K.energy
    b = _body(host)
    E.epoc(b, True, 50.0, 1.0)
    assert b.epoc is not None
    billed = b.eeDay
    pool = b.epoc
    for _ in range(600):                                   # 10 idle hours: 20 tau
        E.epoc(b, False, 0.0, 1.0)
    assert b.epoc is None
    assert b.eeDay == pytest.approx(billed + pool, rel=1e-9)   # the pruned remainder is billed, not dropped
    rel, healed = E.epoc(b, False, 0.0, 1.0)
    assert rel == 0 and b.epoc is None                     # nothing runs on a pruned pool
    E.epoc(b, True, 50.0, 1.0)
    assert b.epoc is not None and b.epoc > 0               # a later set re-creates it


def test_the_after_burn_is_f_of_the_bouts_net_kcal(bout):
    (rows, be, _), (idle, _, _) = bout
    net, _ = _net(rows, be)
    extra = rows[-1]["body.eeDay"] - idle[-1]["body.eeDay"]     # the bout's activity above idle plus the release
    released = extra - net
    total = released + (rows[-1].get("body.epoc") or 0)   # 24 tau leaves under the floor: pruned to nil
    assert total == pytest.approx(be.K.energy.EPOC_F * net, rel=0.01)
    assert released == pytest.approx(be.K.energy.EPOC_F * net, rel=0.01)   # 12 h is 24 tau: all of it released
    assert 0.048 <= released / net <= 0.152               # inside the rows' 4.8-15.2 % (a reading; S1779, S1777)


def test_the_old_tail_is_gone(bout):
    (rows, be, rates), (idle, _, _) = bout
    net, w = _net(rows, be)
    after = BOUT[1] + 6 * 60
    tail = (rows[after - 1]["body.eeDay"] - rows[BOUT[1] - 1]["body.eeDay"]) - \
           (idle[after - 1]["body.eeDay"] - idle[BOUT[1] - 1]["body.eeDay"])
    assert 0 < tail <= be.K.energy.EPOC_F * net + 1e-9    # within the pool
    E = be.K.energy
    old = sum((E.COMPENDIUM[E.classOf(rates[m])] - E.COMPENDIUM.Default) * w / 60 for m in range(BOUT[1], after))
    assert old > 300 and tail < 0.1 * LIVE_TAIL_KCAL      # the rate alone on the same inputs: the live-sized tail


def test_the_lag_steps_on_the_exercise_kcal_alone(bout):
    # L stepped by hand on the exercise kcal each drain banks (exKcalDay's rise) reproduces the record's: the pool's
    # release, billed in every minute after the bout, never enters it
    (rows, be, _), _ = bout
    assert rows[-1]["satiety.L"] > 0
    L = rows[0]["satiety.L"]
    for m in range(1, MINUTES):
        L = be.K.deficit.exerciseLag(L, rows[m]["body.exKcalDay"] - rows[m - 1]["body.exKcalDay"], 1 / 60)
    assert rows[-1]["satiety.L"] == pytest.approx(L, rel=1e-9)


def test_an_idle_day_lays_no_pool(bout):
    _, (idle, _, _) = bout
    assert all(r.get("body.epoc") is None for r in idle) and all(r["body.met"] == 1.3 for r in idle)


# --- the live replay takes the activity from the ring's exogenous fields ----------------------------------------------

RING_PATHS = ("body.met", "body.exKcalDay", "body.epoc", "satiety.L", "body.energyState")
A0 = 1000.0
SLOT = r"""
function(u)
    local NR = NutritionRevamp
    local K = NR.kernel
    return K.json.encode({ gen = 1, rec = K.store.inputsOnly(NR.server.store.records[u]), done = true },
                         NR.server.store.file.fmt)
end
"""


def ring_live_run():
    """A stand-in live server whose engine rate follows the lag through a 40-minute set; its ring page and slot line."""
    a = RL.ServerReplay(start=None, user="admin", hour_offset=7.0,
                        stats={"HUNGER": 0.3, "THIRST": 0.2, "FATIGUE": 0.1, "NICOTINE_WITHDRAWAL": 0.0})
    age = A0
    for _ in range(20):
        age += 1 / 60
        a.step(age)
    slot = a.rt.eval(SLOT)("admin")
    a.rt.execute(STUB_TK)
    a.rt.execute("TK.now = function() return 0 end")
    load(a.h, section(CORE, "-- ==== Plan 11f Task 1 additions (H1)"), "@PZTestKit_Core.lua")
    load(a.h, section(SERVER, "-- ==== Plan 11f Task 1 additions (H2)"), "@PZTestKit_Server.lua")
    TK = a.G.TK
    armed = TK.commands["minute.ring"](a.rt.table("admin", "start", *RING_PATHS))
    assert armed.ok is True, armed
    bout = (10, 50)
    rates = engine_rates(150, bout)
    u = a.R.u["admin"]
    for m in range(150):
        u.raw = rates[m]                                   # the engine's raw rate, which the harness samples
        u.exercising = bout[0] <= m < bout[1]
        age += 1 / 60
        a.step(age)
    page = TK.commands["minute.ring"](a.rt.table("admin", "read"))
    doc = RL.to_py(a.lua51, TK.results[page.result])
    return slot, json.loads(json.dumps(doc))


@pytest.fixture(scope="module")
def ring_live():
    return ring_live_run()


def test_the_ring_carries_the_raw_rate_and_the_flag(ring_live):
    _, doc = ring_live
    rows, _ = RL.load_ring([doc])
    assert RL.ring_carries_activity(rows)
    assert any(r["exe"] is True for r in rows) and any(r["exe"] is False for r in rows)
    evs = RL.ring_activity_events(rows)
    assert all(set(e) <= {"s", "kind", "label", "raw", "exercising"} for e in evs)
    assert not any("met" in e for e in evs)


def test_the_live_replay_reproduces_the_bill_from_the_exogenous_inputs(ring_live):
    slot, doc = ring_live
    rows, paths = RL.load_ring([doc])
    out, be = RL.replay_live(rows, [], slot, ring_paths=paths, sleep_allowed=True)
    assert be.ring_activity
    by_s = {r["s"]: r for r in rows}
    compared = 0
    for r in out:
        live_row = by_s.get(r["s"])
        if live_row is None:
            continue
        for f in RING_PATHS:
            if live_row.get(f) is None:
                assert r.get(f) is None, (r["s"], f, r.get(f))
                continue
            assert r[f] == pytest.approx(live_row[f], rel=1e-9, abs=1e-12), (r["s"], f, r[f], live_row[f])
        compared += 1
    assert compared == len(rows) - 1
    assert {by_s[s]["body.met"] for s in by_s} >= {6.0, 1.3}
    d = RL.diff(out, rows, tol={"body.met": ("abs", 0.0), "satiety.L": ("rel", 1e-9)})
    assert d["ok"], d


def test_without_the_ring_activity_the_bill_is_not_reproduced(ring_live):
    slot, doc = ring_live
    rows, paths = RL.load_ring([doc])
    out, _ = RL.replay_live(rows, [], slot, ring_paths=paths, sleep_allowed=True, ring_activity=False)
    d = RL.diff(out, rows, tol={"body.met": ("abs", 0.0)})
    assert not d["ok"]


def test_a_logged_activity_input_is_refused_beside_the_rings(ring_live):
    slot, doc = ring_live
    rows, paths = RL.load_ring([doc])
    ev = [{"s": rows[3]["s"], "kind": "activity", "rate": 6.0}]
    with pytest.raises(ValueError, match="ring"):
        RL.replay_live(rows, ev, slot, ring_paths=paths, sleep_allowed=True)
    ok = [{"s": rows[3]["s"], "kind": "activity", "moving": False}]
    RL.replay_live(rows, ok, slot, ring_paths=paths, sleep_allowed=True)


def test_ring_activity_events_emit_on_change_and_skip_offline_rows():
    rows = [{"s": 1, "age": 1.0, "rate": 1.5, "exe": False}, {"s": 2, "age": 1.1, "rate": 1.5, "exe": False},
            {"s": 3, "age": 1.2, "rate": 1.6}, {"s": 4, "age": 1.3, "on": False, "rate": 9.0, "exe": True},
            {"s": 5, "age": 1.4, "exe": True}, {"s": 6, "age": 1.5}]
    evs = RL.ring_activity_events(rows)
    assert evs == [{"s": 1, "kind": "activity", "label": "ring-activity", "raw": 1.5, "exercising": False},
                   {"s": 3, "kind": "activity", "label": "ring-activity", "raw": 1.6, "exercising": False},
                   {"s": 5, "kind": "activity", "label": "ring-activity", "raw": 1.6, "exercising": True}]
    assert not RL.ring_carries_activity([{"s": 1, "age": 1.0}])


def test_a_set_ended_by_walking_away_bills_walking_at_most_while_the_rate_falls(met_host):
    h = met_host
    _reset(h)
    p = player(h, rate=6.0, exe="squats", moving=False)
    record = fresh(h, p)
    p.cfg.exe = None
    p.cfg.moving = True                                   # the player walks off: the flag clears
    p.cfg.rate = 5.0                                      # the falling rate would class DiggingSpade
    pipe = h.rt.table()
    minute(h, p, record, 100.0 + 1 / 60, pipe)
    assert pipe["activityClass"] == "Walking5kmh"
    assert record["body"]["met"] == 3.8                   # Walking5kmh, not the falling rate's 5.0
    p.cfg.rate = 4.0                                      # still falling, still moving
    minute(h, p, record, 100.0 + 2 / 60, pipe)
    assert record["body"]["met"] == 3.8
    p.cfg.rate = 3.1                                      # settled at the walking rate, still capped at its class
    minute(h, p, record, 100.0 + 3 / 60, pipe)
    assert record["body"]["met"] == 3.8


def test_a_fall_under_a_constant_load_is_a_fall_of_the_raw_rate(met_host):
    # the carried load is constant; the raw rate falls (4.0 f to 3.8 f), the stripped one with it: a fall on either basis
    h = met_host
    _reset(h)
    f = 1 + 0.35 * 0.5 * 0.5
    p = player(h, rate=4.0 * f, carried=10.0, maxW=20, moving=False)
    record = fresh(h, p)
    p.cfg.rate = 3.8 * f
    minute(h, p, record, 100.0 + 1 / 60)
    assert record["body"]["met"] == 1.3


def test_a_post_set_fall_with_a_load_drop_mid_fall_bills_idle_on_every_still_minute(met_host):
    # Plan 11f ruling C26-1 (F-T6r-3): the engine's raw rate lags toward base x load factor; an eat drops the
    # inventory load (lf 1.0875 to 1.0) at once while the raw rate still carries the old load. The stripped rate
    # (raw / new lf) then rises over the previous minute's although the raw rate fell: a stripped comparison missed it
    h = met_host
    _reset(h)
    lf_loaded = 1 + 0.35 * 0.5 * 0.5
    p = player(h, rate=6.0 * lf_loaded, carried=10.0, maxW=20, exe="squats", moving=False)
    record = fresh(h, p)
    p.cfg.exe = None
    raw = 6.0 * lf_loaded
    prev_stripped = None
    misses = 0
    for m in range(1, 15):
        lf = lf_loaded if m < 8 else 1.0                  # the eat at minute 8 drops the load
        if m == 8:
            p.cfg.carried = 0.0
        raw += (1.5 * lf - raw) * 0.12                    # the lag toward base x lf
        p.cfg.rate = raw
        stripped = raw / lf
        if prev_stripped is not None and stripped >= prev_stripped:
            misses += 1                                   # a stripped comparison reads no fall here
        prev_stripped = stripped
        minute(h, p, record, 100.0 + m / 60)
        assert record["body"]["met"] == 1.3, (m, raw)
    assert misses >= 1                                    # the scenario really does lift the stripped rate


def test_a_departure_and_a_first_sight_clear_the_held_rate_and_flag(met_host):
    h = met_host
    _reset(h)
    p = player(h, rate=6.0, exe="squats", moving=False)
    fresh(h, p)
    m = MET(h)
    keys = [k for k in m.prevRate.keys()]
    assert keys and m.prevExe[keys[0]] is True
    m.forget(keys[0])
    assert m.prevRate[keys[0]] is None and m.prevExe[keys[0]] is None


def test_the_forget_hook_is_wired_to_departure_and_first_sight():
    import lupa.lua51 as lua51
    from .test_metabolism_shape import CORE, SERVER
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    ld = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    with open(CORE, encoding="utf-8") as fh:
        ld(fh.read(), "@NR_Core.lua")()
    rt.execute("""
        NR_STARTED = {}
        Events = { OnServerStarted = { Add = function(fn) NR_STARTED[#NR_STARTED + 1] = fn end } }
        isServer = function() return true end
        SandboxVars = { Nutrition = false }
        NutritionRevamp.server.players = { onFirstSight = {}, onDeparture = {} }
    """)
    for n in sorted(["NR_Server_Metabolism.lua", "NR_Server_Kinetics.lua", "NR_Server_Minute.lua"]):
        with open(os.path.join(SERVER, n), encoding="utf-8") as fh:
            ld(fh.read(), "@" + n)()
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")           # once
    G = rt.globals()
    met = G.NutritionRevamp.server.metabolism
    same = rt.eval("rawequal")
    P = G.NutritionRevamp.server.players
    for hook_list in (P.onFirstSight, P.onDeparture):
        hooks = [hook_list[i] for i in range(1, len(hook_list) + 1)]
        assert len([x for x in hooks if same(x, met.forget)]) == 1
        for x in hooks:
            met.prevRate["a"] = 1.5
            met.prevExe["a"] = True
            x("a", None, None)
            if same(x, met.forget):
                assert met.prevRate["a"] is None and met.prevExe["a"] is None


def test_ring_activity_events_never_mark_a_row_between_f_t7_1(ring_live):
    """F-T7-1: the engine's raw rate changes on nearly every row of a lagged bout, and the diff graded 0 rows."""
    slot, doc = ring_live
    rows, paths = RL.load_ring([doc])
    out, be = RL.replay_live(rows, [], slot, ring_paths=paths, sleep_allowed=True)
    assert len(be.ring_activity) > 20                   # an event on many rows
    assert not any(r["between"] for r in out)
    assert sum(r["ringEvents"] for r in out) == len(be.ring_activity)
    d = RL.diff(out, rows, tol={"body.energyState": ("abs", 1e-9)})
    assert d["ok"] and d["fields"]["body.energyState"]["n"] == len(rows) - 1 and d["skipped"] == [], d


def test_a_perturbed_output_is_still_caught_with_ring_activity_on(ring_live):
    slot, doc = ring_live
    rows, paths = RL.load_ring([doc])
    out, _ = RL.replay_live(rows, [], slot, ring_paths=paths, sleep_allowed=True)
    bad = [dict(r) for r in rows]
    victim = next(r for r in bad if r["s"] == rows[30]["s"])
    victim["body.energyState"] += 0.01
    d = RL.diff(out, bad, tol={"body.energyState": ("abs", 1e-6)})
    assert not d["ok"]
    assert any(f.get("s") == victim["s"] for f in d["findings"]), d["findings"]


def test_a_logged_drink_still_marks_its_next_row_between_beside_the_rings(ring_live):
    slot, doc = ring_live
    rows, paths = RL.load_ring([doc])
    ev = [{"s": rows[10]["s"], "kind": "drink", "fluid": "Water", "litres": 0.3}]
    out, _ = RL.replay_live(rows, ev, slot, ring_paths=paths, sleep_allowed=True)
    assert sum(r["between"] for r in out) == 1


def test_the_replay_holds_the_rings_raw_rate_for_the_fall_gate_under_a_load():
    # Plan 11f ruling C26-1: the stand-in answers the ring's raw rate as is and the mod holds that raw value, never
    # the rate with the stand-in's load factor divided out (inv 10 of maxW 20: 1.0875)
    a = RL.ServerReplay(start=None, user="admin", hour_offset=7.0, player={"inv": 10.0, "maxW": 20.0},
                        stats={"HUNGER": 0.3, "THIRST": 0.2, "FATIGUE": 0.1, "NICOTINE_WITHDRAWAL": 0.0})
    age = A0
    u = a.R.u["admin"]
    for raw in (4.2, 4.1, 4.0):
        u.raw = raw
        age += 1 / 60
        a.step(age)
        assert a.NR.server.metabolism.prevRate["admin"] == raw

