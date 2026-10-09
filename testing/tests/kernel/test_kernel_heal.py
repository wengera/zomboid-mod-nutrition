"""The body record's self-heal in the kernel (NR_Kernel_Heal.lua, K.heal), Plan 10 Task R3.

NR_Kernel_Heal.lua is a kernel file, so the session `host` fixture loads it through its glob and the coverage
gate sees every line. The behaviour assertions are test_metabolism_shape.py's heal tests, ported to call
K.heal.body(body, ageH, l0) directly; the adapter keeps the counting and the log, and its engine read (the
Strength level, made only when body.l0 is not finite) is the l0 argument. The property test runs 500 seeded
cases: every healed field made non-finite comes back finite, and the names returned are exactly the fields that
were not finite.
"""
import math
import random

TOL = 1e-9
NAN = float("nan")
INF = float("inf")

SCALARS = ["fm0", "lm0", "fm", "lm", "fmRef", "pPrevKg", "dayIndex", "lastAgeH",
           "energyState", "dmod", "rmod", "tac", "at", "n", "vStr", "vHyp", "vStrHigh", "inDay", "eeDay", "ebDay",
           "actKcalDay", "exKcalDay", "pDay", "carbDay", "lipDay", "alcDay", "metMinDay", "band1Day", "band2Day",
           "cumDef", "r", "traitCarry", "tDisuse", "nPeak", "l0", "lm0dis", "tPeakD"]
RINGS7 = ["mass7", "eb7", "p7"]
TRAIL_KEYS = ["kcal", "ee", "ex", "p", "carb", "lip"]


def heal(h, body, age, l0=None):
    return h.K.heal.body(body, age, l0)


def new_body(h, age=100.0, sex=1, l0=3):
    body = h.K.body.new(80.0, sex, h.rt.table(), l0, 1.0, 1.0, age)
    heal(h, body, age)                                      # the first pass heals mass7's empty slots
    return body


def names(bad):
    return [] if bad is None else bad.split(",")


def finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def all_finite(h, body):
    for k in SCALARS:
        assert finite(body[k]), k
    for k in RINGS7:
        for i in range(1, 8):
            assert finite(body[k][i]), (k, i)
    for i in range(1, h.K.strength.MEM_HOLD_DAYS + 1):
        assert finite(body["nHist"][i]), ("nHist", i)
    for i in range(1, 8):
        assert finite(body["bandWeek"][i][1]) and finite(body["bandWeek"][i][2]), ("bandWeek", i)
    assert finite(body["trail"]["at"])
    for k in TRAIL_KEYS:
        for i in range(1, 26):
            assert finite(body["trail"][k][i]), ("trail", k, i)


def test_a_healthy_body_heals_nothing(host):
    body = new_body(host)
    assert heal(host, body, 100.5) is None


def test_mark_joins_names_in_order(host):
    assert host.K.heal.mark(None, "fm") == "fm"
    assert host.K.heal.mark("fm", "tac") == "fm,tac"


def test_a_non_finite_stamp_heals_and_is_named(host):
    h = host
    body = new_body(h)
    body.fm = NAN
    body.tac = NAN
    body.eb7[3] = NAN
    bad = heal(h, body, 100.0)
    assert names(bad) == ["fm", "tac", "eb7"]
    assert abs(body["fm"] - body["fm0"]) < TOL
    assert body["tac"] == 1.0 and body["eb7"][3] == 0
    all_finite(h, body)


def test_day_index_ages_and_creation_masses(host):
    h = host
    body = new_body(h)
    body.dayIndex = NAN
    body.lastAgeH = INF
    body.fm0 = NAN
    body.lm0 = NAN
    bad = heal(h, body, 168.0)
    assert body["dayIndex"] == 7
    assert body["lastAgeH"] == 168.0
    assert body["fm0"] == body["fm"] and body["lm0"] == body["lm"]
    assert names(bad) == ["fm0", "lm0", "dayIndex", "lastAgeH"]


def test_creation_masses_fall_back_to_the_split_by_sex(host):
    h = host
    for sex in (1, 2):
        body = new_body(h, sex=sex)
        body.fm = NAN
        body.fm0 = NAN
        body.lm = NAN
        body.lm0 = NAN
        bad = heal(h, body, 100.0)
        fm, lm, _ = h.K.body.split(80, sex, h.rt.table())
        assert abs(body["fm0"] - fm) < TOL and abs(body["lm0"] - lm) < TOL
        assert abs(body["fm"] - fm) < TOL and abs(body["lm"] - lm) < TOL
        assert names(bad)[:4] == ["fm0", "lm0", "fm", "lm"]
        all_finite(h, body)


def test_non_finite_ring_slots(host):
    h = host
    body = new_body(h)
    body.p7[2] = NAN
    body.eb7[7] = INF
    body.mass7[1] = NAN
    bad = heal(h, body, 100.0)
    assert body["p7"][2] == 0 and body["eb7"][7] == 0
    assert abs(body["mass7"][1] - (body["fm"] + body["lm"])) < 1e-6
    assert names(bad) == ["mass7", "eb7", "p7"]


def test_a_ring_its_read_sees_non_finite_heals_and_is_named_once_a_slot(host):
    # Plan 11d Task 9c: the trailing-24 h window. The current hour (slot 1 at age 100) and the oldest hour (slot 2,
    # hour 76) are in every read; a non-finite one sends the heal through the rings, which zeroes every non-finite
    # slot and names its ring once a slot zeroed (Task 9d: K.body.trailRingSum's count)
    h = host
    body = new_body(h)
    t = body.trail
    h.K.body.trail24(t, "kcal")                         # the closed sums built for hour 100
    t.kcal[1] = NAN
    t.carb[2] = -INF
    t.carb[10] = NAN                                    # hour 84, a closed hour: zeroed and counted on the same walk
    bad = heal(h, body, 100.5)
    assert names(bad) == ["trail.kcal", "trail.carb", "trail.carb"]
    assert t["at"] == 100.0 and t.kcal[1] == 0 and t.carb[2] == 0 and t.carb[10] == 0 and t.ch == 100
    assert heal(h, body, 100.5) is None


def test_a_non_finite_window_age_empties_every_ring_and_is_named(host):
    # Plan 11d Task 9d (the Task 9c review): with its age lost no slot's hour is known, so every ring takes
    # K.body.newTrail(ageH)'s values, finite or not, and only the age is named
    h = host
    body = new_body(h)
    t = body.trail
    for k in TRAIL_KEYS:
        for i in range(1, 26):
            t[k][i] = float(i)
    t.kcal[3] = NAN
    h.K.body.trail24(t, "ee")
    t.at = NAN
    bad = heal(h, body, 130.25)
    assert names(bad) == ["trail.at"]
    fresh = h.py(h.K.body.newTrail(130.25))
    got = h.py(t)
    for k in TRAIL_KEYS:
        assert list(got[k].values()) == list(fresh[k].values()), k
        assert got["c"][k] == 0, k
    assert t["at"] == 130.25 and t.ch == -1
    assert heal(h, body, 130.25) is None


def test_a_closed_hour_turned_non_finite_is_zeroed_and_named_by_the_heal_at_the_turn(host):
    # a closed hour's slot is read only through the closed sums, which stand for the hour they were built in; no step
    # writes a closed hour (the guard covers the current one). Plan 11d Task 9d (the Task 9c review): the heal at the
    # first minute of a new hour walks the rings before the window moves, so the slot is zeroed and named there, not
    # by a reader's rebuild unnamed; two in one ring are named twice
    h = host
    body = new_body(h)
    t = body.trail
    h.K.body.trail24(t, "ee")                           # the closed sums built for hour 100
    t.ee[10] = NAN                                      # hour 84, inside the closed hours
    t.ee[11] = INF                                      # hour 85
    assert heal(h, body, 100.5) is None                 # unread: the sums stand
    assert names(heal(h, body, 101.0)) == ["trail.ee", "trail.ee"]
    assert t.ee[10] == 0 and t.ee[11] == 0 and t.ch == 100
    h.K.body.trailTo(t, 101.0)
    assert h.K.body.trail24(t, "ee") == 0 and t.ch == 101
    assert heal(h, body, 101.5) is None


def test_creation_scalars_and_the_strength_and_band_rings(host):
    h = host
    body = new_body(h)
    body.r = NAN
    body.traitCarry = INF
    body.l0 = NAN
    body.tDisuse = NAN
    body.lm0dis = NAN
    body.nPeak = NAN
    body.tPeakD = NAN
    body.exKcalDay = NAN
    body.nHist[3] = NAN
    body.bandWeek[2][1] = NAN
    body.bandWeek[5][2] = -INF
    bad = heal(h, body, 100.0, 7)
    assert body["r"] == 1 and body["traitCarry"] == 1
    assert body["l0"] == 7
    assert body["tDisuse"] == 0 and body["nPeak"] == 0
    assert body["lm0dis"] == body["lm"]
    assert body["tPeakD"] == body["dayIndex"]
    assert body["exKcalDay"] == 0
    assert body["nHist"][3] == 0
    assert body["bandWeek"][2][1] == 0 and body["bandWeek"][5][2] == 0
    assert names(bad) == ["exKcalDay", "r", "traitCarry", "tDisuse", "nPeak", "l0", "lm0dis", "tPeakD", "nHist",
                          "bandWeek", "bandWeek"]
    all_finite(h, body)


def test_l0_without_a_finite_reading_heals_to_zero(host):
    h = host
    for reading in (None, NAN):
        body = new_body(h)
        body.l0 = NAN
        assert names(heal(h, body, 100.0, reading)) == ["l0"]
        assert body["l0"] == 0


def test_every_field_nan_comes_back_finite_and_named(host):
    h = host
    body = new_body(h)
    for k in SCALARS:
        body[k] = NAN
    for k in RINGS7:
        for i in range(1, 8):
            body[k][i] = NAN
    for i in range(1, h.K.strength.MEM_HOLD_DAYS + 1):
        body["nHist"][i] = NAN
    for i in range(1, 8):
        body["bandWeek"][i][1] = NAN
        body["bandWeek"][i][2] = NAN
    body.trail.at = NAN
    for k in TRAIL_KEYS:
        for i in range(1, 26):
            body.trail[k][i] = NAN
    bad = heal(h, body, 130.0, 4)
    all_finite(h, body)
    # the window: its age is named and every ring emptied (Plan 11d Task 9d), so no ring is named
    assert set(names(bad)) == set(SCALARS) | set(RINGS7) | {"nHist", "bandWeek", "trail.at"}


def test_heal_property_seeded(host):
    h = host
    rng = random.Random(3310)
    hold = h.K.strength.MEM_HOLD_DAYS
    for case in range(500):
        age = rng.uniform(0, 5000)
        body = new_body(h, age=age, sex=rng.choice([1, 2]), l0=rng.randint(0, 10))
        p = 1.0 if case % 10 == 0 else rng.random()
        bad_vals = (NAN, INF, -INF)
        expect = set()
        for k in SCALARS:
            if rng.random() < p:
                body[k] = rng.choice(bad_vals)
                expect.add(k)
        for k in RINGS7:
            for i in range(1, 8):
                if rng.random() < p:
                    body[k][i] = rng.choice(bad_vals)
                    expect.add(k)
        for i in range(1, hold + 1):
            if rng.random() < p:
                body["nHist"][i] = rng.choice(bad_vals)
                expect.add("nHist")
        for i in range(1, 8):
            for j in (1, 2):
                if rng.random() < p:
                    body["bandWeek"][i][j] = rng.choice(bad_vals)
                    expect.add("bandWeek")
        l0 = rng.choice([None, NAN, rng.randint(0, 10)])
        bad = heal(h, body, age + rng.uniform(0, 48), l0)
        all_finite(h, body)
        assert set(names(bad)) == expect, case
        assert heal(h, body, age) is None                    # a healed body heals nothing more


# The post-step guard (Plan 11 Task 12, ruling 10): K.heal.snap copies the guarded keys before the step, and
# K.heal.guard re-stamps from the copy every guarded key the step left non-finite.
def test_guard_restamps_only_non_finite_keys_from_the_snapshot(host):
    t = host.rt.eval("{ a = 1, b = 2, c = 3 }")
    keys = host.rt.table("a", "b")
    snap = host.call("heal.snap", t, keys, host.rt.table())
    t.a, t.b, t.c = host.rt.eval("0/0"), 5, host.rt.eval("1/0")
    assert host.call("heal.guard", t, keys, snap) == 1
    assert t.a == 1 and t.b == 5                       # c is not guarded: left for the next pre-step heal


def test_guard_leaves_a_key_whose_snapshot_is_not_finite(host):
    t = host.rt.eval("{ a = 0/0 }")
    keys = host.rt.table("a")
    snap = host.rt.eval("{ a = 0/0 }")
    assert host.call("heal.guard", t, keys, snap) == 0


def test_guard_restamps_both_infinities_and_reuses_the_snapshot_table(host):
    t = host.rt.eval("{ a = 1, b = 2 }")
    keys = host.rt.table("a", "b")
    out = host.rt.table()
    same = host.rt.eval("function(a, b) return rawequal(a, b) end")
    assert same(host.call("heal.snap", t, keys, out), out)      # filled in place: no allocation per minute
    t.a, t.b = host.rt.eval("1/0"), host.rt.eval("-1/0")
    assert host.call("heal.guard", t, keys, out) == 2
    assert t.a == 1 and t.b == 2
    t.a = "text"                                                 # a non-number is never touched
    assert host.call("heal.guard", t, keys, out) == 0
    assert t.a == "text"
