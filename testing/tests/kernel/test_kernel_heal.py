"""The body record's self-heal in the kernel (NR_Kernel_Heal.lua, K.heal), Plan 10 Task R3; the lean-mass body's
fields since Plan 13 Task 12.

NR_Kernel_Heal.lua is a kernel file, so the session `host` fixture loads it through its glob and the coverage
gate sees every line. The behaviour assertions are test_metabolism_shape.py's heal tests, ported to call
K.heal.body(body, ageH, specific, P, dayFloor) directly; the adapter keeps the counting and the log and passes the
effective-sex option, the strength table and the record-day lower bound (it reads no engine value). The creation
fields (lm, fm, F0, Fc, Pk) heal to the no-trait body's (K.body.create(nil, nil, P) at the effective sex). The
property test runs 500 seeded cases: every healed field made non-finite comes back finite, and the names returned are
exactly the fields that were not finite.
"""
import math
import random

TOL = 1e-9
NAN = float("nan")
INF = float("inf")

SCALARS = ["lm", "fm", "F0", "Fc", "Pk", "fmRef", "pPrevKg", "dayIndex", "dayStartH", "lastAgeH",
           "energyState", "rmod", "tac", "at", "inDay", "eeDay", "ebDay", "actKcalDay", "exKcalDay", "pDay",
           "carbDay", "lipDay", "alcDay", "metMinDay", "band1Day", "band2Day", "tDisuse", "lx", "grace", "Tgrace",
           "sigDay", "S", "N0", "T", "fatT", "thinT", "lm0dis"]
RINGS7 = ["mass7", "eb7", "p7", "sig7"]
TRAIL_KEYS = ["kcal", "ee", "ex", "p", "carb", "lip"]
MUSCLES = [None, "WEAK", "FEEBLE", "STOUT", "STRONG"]


def heal(h, body, age, specific=None, P=None, day_floor=None):
    return h.K.heal.body(body, age, specific, P, day_floor)


def new_body(h, age=100.0, sex=1, muscle="STOUT", weight=None):
    D = h.K.strength.DEFAULTS
    body = h.K.body.new(h.K.body.create(muscle, weight, D, h.K.body.effSex(sex, False)), sex, age)
    heal(h, body, age)
    return body


def no_trait(h, sex_idx=1, P=None):
    return h.py(h.K.body.create(None, None, P or h.K.strength.DEFAULTS, sex_idx))


def test_the_heal_rebuilds_masses_at_the_effective_sex(host):
    # Plan 13 Task 3 fix 1, Task 12: a lost fm or lm heals to the no-trait body's at K.body.effSex(body.sex, specific)
    male, female = no_trait(host, 1), no_trait(host, 2)
    assert male["fm"] != female["fm"]
    for specific, want in ((None, male), (False, male), (True, female)):
        body = new_body(host, sex=2)
        body["fm"] = NAN
        body["lm"] = NAN
        host.K.heal.body(body, 100.0, specific)
        assert (body["fm"], body["lm"]) == (want["fm"], want["lm"]), specific
        assert body["sex"] == 2
    body = new_body(host, sex=1)
    body["fm"] = NAN
    host.K.heal.body(body, 100.0, True)
    assert body["fm"] == male["fm"]


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
    for i in range(1, 8):
        assert finite(body["bandWeek"][i][1]) and finite(body["bandWeek"][i][2]), ("bandWeek", i)
    assert finite(body["trail"]["at"])
    for k in TRAIL_KEYS:
        for i in range(1, 26):
            assert finite(body["trail"][k][i]), ("trail", k, i)


def test_a_healthy_body_heals_nothing(host):
    for m in MUSCLES:
        for w in (None, "OBESE", "UNDERWEIGHT", "VERY_UNDERWEIGHT"):
            body = new_body(host, muscle=m, weight=w)
            assert heal(host, body, 100.5) is None, (m, w)


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
    assert body["fm"] == no_trait(h)["fm"]
    assert body["tac"] == 1.0 and body["eb7"][3] == 0
    all_finite(h, body)


def test_a_nan_f0_rebuilds_to_the_no_trait_body(host):
    # the brief: a non-finite F0 heals to the no-trait body's set point; the held lean and the other fields stand
    h = host
    body = new_body(h, muscle="STRONG")
    lm = body.lm
    body.F0 = NAN
    assert names(heal(h, body, 100.0)) == ["F0"]
    assert body["F0"] == no_trait(h)["F0"] and body["lm"] == lm


def test_the_creation_fields_heal_to_the_no_trait_body_of_the_servers_table(host):
    # bodyBase's P: a tuned server's cap holds through the heal (P passed in, nil reading DEFAULTS)
    h = host
    P, _ = h.K.strength.params(h.table({"StrengthCapLevel": 14}))
    want = no_trait(h, 1, P)
    assert want["Fc"] != no_trait(h)["Fc"]
    body = new_body(h)
    for k in ("lm", "fm", "F0", "Fc", "Pk"):
        body[k] = NAN
    assert names(heal(h, body, 100.0, False, P)) == ["lm", "fm", "F0", "Fc", "Pk"]
    for k in ("lm", "fm", "F0", "Fc", "Pk"):
        assert body[k] == want[k], k


def test_n0_and_t_heal_to_the_no_trait_one(host):
    h = host
    body = new_body(h, muscle="STRONG")
    body.N0 = NAN
    body.T = -INF
    body.Tgrace = NAN
    body.grace = INF
    body.lx = NAN
    body.sigDay = NAN
    body.S = NAN
    bad = heal(h, body, 100.0)
    assert names(bad) == ["lx", "grace", "Tgrace", "sigDay", "S", "N0", "T"]
    assert (body.N0, body.T, body.Tgrace, body.grace, body.lx, body.sigDay, body.S) == (1, 1, 0, 0, 0, 0, 0)


def test_day_index_ages_and_the_record_day_floor(host):
    # Task 12 amendment 5: tPeakD is removed, so a lost dayIndex heals to the record-day lower bound the adapter passes
    h = host
    body = new_body(h)
    body.dayIndex = NAN
    body.dayStartH = NAN
    body.lastAgeH = INF
    bad = heal(h, body, 168.0, None, None, 3)
    assert body["dayIndex"] == 3                            # the record's day, never the world's 7 (ruling 13-5)
    assert body["dayStartH"] == 168.0                       # the world day's start at the heal's age (Plan 16 Task 2)
    assert body["lastAgeH"] == 168.0
    assert names(bad) == ["dayIndex", "dayStartH", "lastAgeH"]


def test_day_index_falls_back_to_the_birth_day_without_a_record_day(host):
    # Plan 16 Task 2 (the successor of test_day_index_falls_back_to_the_world_day_without_a_record_day): with no
    # surviving record day the birth day floor(bornAge / 24) counts no offline day; with no birth age, the world day
    h = host
    for floor in (None, NAN):
        body = new_body(h)                                  # born at 100.0: record day 4
        body.dayIndex = NAN
        assert names(heal(h, body, 168.0, None, None, floor)) == ["dayIndex"]
        assert body["dayIndex"] == 4
    body = new_body(h)
    body.dayIndex = NAN
    body.bornAge = NAN
    assert names(heal(h, body, 168.0)) == ["dayIndex"]
    assert body["dayIndex"] == 7


def test_the_rungs_heal_when_not_a_whole_number_in_range(host):
    # Task 12 amendment 4: fatT a whole number in 0..2, thinT in 0..3, else 0
    h = host
    for fat, thin, bad_names in ((2, 3, []), (0, 0, []), (3, 0, ["fatT"]), (-1, 4, ["fatT", "thinT"]),
                                 (1.5, 2.5, ["fatT", "thinT"]), (NAN, INF, ["fatT", "thinT"]), (1, -INF, ["thinT"])):
        body = new_body(h)
        body.fatT = fat
        body.thinT = thin
        assert names(heal(h, body, 100.0)) == bad_names, (fat, thin)
        assert body.fatT == (fat if "fatT" not in bad_names else 0)
        assert body.thinT == (thin if "thinT" not in bad_names else 0)
    body = new_body(h)
    body.fatT = "obese"                                     # a value of another type is not a rung either
    assert names(heal(h, body, 100.0)) == ["fatT"] and body.fatT == 0


def test_non_finite_ring_slots(host):
    h = host
    body = new_body(h)
    body.lx = 1.5
    body.p7[2] = NAN
    body.eb7[7] = INF
    body.mass7[1] = NAN
    body.sig7[4] = NAN
    bad = heal(h, body, 100.0)
    assert body["p7"][2] == 0 and body["eb7"][7] == 0 and body["sig7"][4] == 0
    assert body["mass7"][1] == body["fm"] + body["lm"] + 1.5     # the body mass, lx in it (ruling 13-20)
    assert names(bad) == ["mass7", "eb7", "p7", "sig7"]


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


def test_a_non_finite_closed_sum_with_no_bad_slot_is_named_and_rebuilt(host):
    # Plan 11d Task 9d fix (the Task 9d review's minor 4): a ring whose read is non-finite through its derived closed sum
    # alone (no slot to zero) is named once and its sum rebuilt; the other rings' sums stand
    h = host
    body = new_body(h)
    t = body.trail
    t.ee[5] = 40.0
    t.ch = -1
    h.K.body.trail24(t, "ee")                           # the closed sums built for hour 100
    t.c.ee = NAN
    t.c.p = 7.0                                         # a stale but finite sum: not read as bad, left
    assert names(heal(h, body, 100.5)) == ["trail.ee"]
    assert t.c.ee == 40.0 and t.c.p == 7.0 and t.ch == 100
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
    body.tDisuse = NAN
    body.lm0dis = NAN
    body.exKcalDay = NAN
    body.Pk = INF
    body.sig7[3] = NAN
    body.bandWeek[2][1] = NAN
    body.bandWeek[5][2] = -INF
    bad = heal(h, body, 100.0)
    assert body["tDisuse"] == 0
    assert body["lm0dis"] == body["lm"]
    assert body["Pk"] == no_trait(h)["Pk"]
    assert body["exKcalDay"] == 0
    assert body["sig7"][3] == 0
    assert body["bandWeek"][2][1] == 0 and body["bandWeek"][5][2] == 0
    assert names(bad) == ["Pk", "exKcalDay", "tDisuse", "lm0dis", "bandWeek", "bandWeek", "sig7"]
    all_finite(h, body)


def test_every_field_nan_comes_back_finite_and_named(host):
    h = host
    body = new_body(h)
    for k in SCALARS:
        body[k] = NAN
    for k in RINGS7:
        for i in range(1, 8):
            body[k][i] = NAN
    for i in range(1, 8):
        body["bandWeek"][i][1] = NAN
        body["bandWeek"][i][2] = NAN
    body.trail.at = NAN
    for k in TRAIL_KEYS:
        for i in range(1, 26):
            body.trail[k][i] = NAN
    bad = heal(h, body, 130.0)
    all_finite(h, body)
    # the window: its age is named and every ring emptied (Plan 11d Task 9d), so no ring is named
    assert set(names(bad)) == set(SCALARS) | set(RINGS7) | {"bandWeek", "trail.at"}


def test_heal_property_seeded(host):
    h = host
    rng = random.Random(3310)
    for case in range(500):
        age = rng.uniform(0, 5000)
        body = new_body(h, age=age, sex=rng.choice([1, 2]), muscle=rng.choice(MUSCLES))
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
        for i in range(1, 8):
            for j in (1, 2):
                if rng.random() < p:
                    body["bandWeek"][i][j] = rng.choice(bad_vals)
                    expect.add("bandWeek")
        floor = rng.choice([None, NAN, rng.randint(0, 200)])
        bad = heal(h, body, age + rng.uniform(0, 48), rng.choice([None, False, True]), None, floor)
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
