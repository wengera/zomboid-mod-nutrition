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

SCALARS = ["fm0", "lm0", "fm", "lm", "fmRef", "pPrevKg", "dayIndex", "lastAgeH", "lastCloseAgeH",
           "energyState", "dmod", "rmod", "tac", "at", "n", "vStr", "vHyp", "vStrHigh", "inDay", "eeDay", "ebDay",
           "actKcalDay", "exKcalDay", "pDay", "carbDay", "lipDay", "alcDay", "metMinDay", "band1Day", "band2Day",
           "cumDef", "r", "traitCarry", "tDisuse", "nPeak", "l0", "lm0dis", "tPeakD"]
RINGS7 = ["mass7", "eb7", "p7", "carb7", "lip7"]


def heal(h, body, age, l0=None):
    return h.K.heal.body(body, age, l0)


def new_body(h, age=100.0, sex=1, l0=3):
    body = h.K.body.new(80.0, sex, h.rt.table(), l0, 1.0, 1.0, age)
    heal(h, body, age)                                      # the backfill of any field K.body.new leaves out
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
    body.lastAgeH = NAN
    body.lastCloseAgeH = INF
    body.fm0 = NAN
    body.lm0 = NAN
    bad = heal(h, body, 168.0)
    assert body["dayIndex"] == 7
    assert body["lastAgeH"] == 168.0 and body["lastCloseAgeH"] == 168.0
    assert body["fm0"] == body["fm"] and body["lm0"] == body["lm"]
    assert names(bad) == ["fm0", "lm0", "dayIndex", "lastAgeH", "lastCloseAgeH"]


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


def test_absent_rings_and_fields_backfill_unnamed(host):
    h = host
    body = new_body(h)
    for k in ("p7", "carb7", "lip7", "eb7", "mass7", "pPrevKg", "lastCloseAgeH", "exKcalDay", "nHist", "bandWeek"):
        body[k] = None
    bad = heal(h, body, 100.5)
    for k in ("p7", "carb7", "lip7", "eb7"):
        assert list(body[k].values()) == [0] * 7, k
    assert body["pPrevKg"] == h.K.aerobic.P_LOW
    assert body["lastCloseAgeH"] == 100.5
    assert body["exKcalDay"] == 0
    assert list(body["nHist"].values()) == [0] * h.K.strength.MEM_HOLD_DAYS
    assert [list(body["bandWeek"][i].values()) for i in range(1, 8)] == [[0, 0]] * 7
    assert names(bad) == ["mass7"] * 7                     # the empty mass7 ring's slots heal to the mass
    assert abs(body["mass7"][1] - (body["fm"] + body["lm"])) < TOL


def test_a_partial_band_week_backfills_its_missing_slots(host):
    h = host
    body = new_body(h)
    body.bandWeek[4] = None
    assert heal(h, body, 100.5) is None
    assert list(body["bandWeek"][4].values()) == [0, 0]


def test_non_finite_ring_slots(host):
    h = host
    body = new_body(h)
    body.p7[2] = NAN
    body.carb7[7] = INF
    body.lip7[4] = NAN
    body.mass7[1] = NAN
    bad = heal(h, body, 100.0)
    assert body["p7"][2] == 0 and body["carb7"][7] == 0 and body["lip7"][4] == 0
    assert abs(body["mass7"][1] - (body["fm"] + body["lm"])) < 1e-6
    assert names(bad) == ["mass7", "p7", "carb7", "lip7"]


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
    bad = heal(h, body, 130.0, 4)
    all_finite(h, body)
    assert set(names(bad)) == set(SCALARS) | set(RINGS7) | {"nHist", "bandWeek"}


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
