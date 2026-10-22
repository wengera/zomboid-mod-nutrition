"""Food hedonics (Plan 19 Task 5; spec docs/superpowers/specs/2026-10-21-dials-and-hedonics-design.md section B.2):
R1 plain energy (the classifier, the online-hour ring, the share and its floor), R2 preparation quality, R3
alliesthesia and R4 the taste class beside the monotony type. Each rule has a test a plausible wrong change fails (the
task's mutation pass): the plain threshold off by its sign, the happy side scaled, the share not rotating, the class
weight ignored. Hand-computed from the registry's dials (conftest.dial_value).
"""
import os

import pytest

from .conftest import dial_line, dial_value

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
KERNEL = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Kernel_Hedonics.lua")
AGE = 1000.0


def H(host):
    return host.K.hedonics


def dv(name):
    return dial_value("hedonics." + name)


# --- the dials --------------------------------------------------------------------------------------------------------


def test_every_magnitude_is_a_hedonics_dial(host):
    h = H(host)
    for name in ("PLAIN_SHARE", "PLAIN_KCAL", "FSOD_FAT", "FSOD_NA", "CSOD_CARB", "CSOD_NA", "FATTY_SHARE",
                 "SHARE_MIN_KCAL", "ALLIES_F", "ALLIES_LEVEL", "CLASS_W", "BUDGET_FAIR", "BUDGET_DEGEN"):
        assert h[name] == dv(name), name
    assert h.FLOOR_KNOTS[1][1] == dv("FLOOR_KNOTS.1.1") and h.FLOOR_KNOTS[1][2] == 0
    assert (h.FLOOR_KNOTS[3][1], h.FLOOR_KNOTS[3][2]) == (dv("FLOOR_KNOTS.3.1"), dv("FLOOR_KNOTS.3.2"))
    assert (h.PREP_KNOTS[1][1], h.PREP_KNOTS[2][2], h.PREP_KNOTS[3][1]) == (0, 1, 10)
    assert h.RING_N == 24


def test_the_rows_name_their_sources():
    assert "S2291" in dial_line("hedonics.FSOD_FAT") and "S2291" in dial_line("hedonics.CSOD_NA")
    allies = dial_line("hedonics.ALLIES_F")
    assert ("game choice; direction from the repletion row (S4.9, Cabanac), disputed by the fasting null "
            "(S4.2, Drewnowski)") in allies and "S2297" in allies and "S2290" in allies
    for knot in ("PREP_KNOTS.1.2", "PREP_KNOTS.3.2"):
        line = dial_line("hedonics." + knot)
        assert "S2298" in line and "S2309" in line
    ceiling = dial_line("hedonics.FLOOR_KNOTS.3.2")
    assert "#2369" in ceiling and "not S2295" in ceiling and "not monotony" in ceiling
    assert "S2294" in dial_line("hedonics.CLASS_W")


# --- R1: the classifier -----------------------------------------------------------------------------------------------


def plain(host, p, c, l, na=0.0, kcal100=400.0, unhappy=0):
    return H(host).isPlain(p, c, l, na, kcal100, unhappy)


def test_a_pure_fat_and_a_pure_sugar_are_plain(host):
    assert plain(host, 0, 0, 100, kcal100=884, unhappy=50) is True      # an oil
    assert plain(host, 0, 100, 0, na=0.001, kcal100=387) is True        # sugar
    assert plain(host, 13, 72, 1.5, kcal100=371, unhappy=40) is True    # dry pasta: 0.82 of its energy is carbohydrate


def test_a_mixed_food_is_not_plain_and_the_threshold_is_at_or_over(host):
    # mutation: the threshold's sign flipped (top > share reads plain) fails here
    assert plain(host, 25, 30, 20) is False                             # a mixed plate
    assert plain(host, 0, 50, 50 * 4 / 9.0) is False                    # half and half
    share = dv("PLAIN_SHARE")
    c = 100.0
    rest = c * (1 - share) / share                                      # protein grams putting carbohydrate at the share
    assert plain(host, rest, c, 0) is True                              # exactly at the share: plain
    assert plain(host, rest * 1.01, c, 0) is False                      # just under it


def test_a_dilute_food_a_treat_and_no_energy_are_not_plain(host):
    assert plain(host, 0.3, 14, 0.2, kcal100=52) is False               # an apple: single-macro but dilute
    assert plain(host, 0, 100, 0, kcal100=394, unhappy=-10) is False    # hard candy: a vanilla treat
    assert plain(host, 0, 0, 0, kcal100=400) is False                   # no macro energy


def test_a_sodium_pairing_is_palatable_not_plain(host):
    # S2291's clusters: fat over 25 % of the energy with sodium at 0.30 % by weight, carbohydrate over 40 % with 0.20 %
    assert plain(host, 0.85, 0.06, 81.1, na=0.643, kcal100=717, unhappy=20) is False    # salted butter
    assert plain(host, 0, 0, 100, na=0.29, kcal100=884) is True                         # just under the fat pairing
    assert plain(host, 10, 80, 3, na=1.24, kcal100=384) is False                        # salted pretzels
    assert plain(host, 10, 80, 3, na=0.19, kcal100=384) is True                         # just under the carb pairing
    assert H(host).paired(0.26, 0, 0.30) is True and H(host).paired(0.25, 0, 0.30) is False
    assert H(host).paired(0, 0.41, 0.20) is True and H(host).paired(0, 0.40, 0.20) is False


def test_the_taste_class_by_precedence(host):
    tc = H(host).tasteClass
    assert tc(13, 72, 1.5, True, True) == "staple"                     # a staple first, whatever else
    assert tc(0.85, 0.06, 81.1, False, False) == "fatty"               # butter
    assert tc(25, 20, 50, False, True) == "fatty"                      # fatty before sweet
    assert tc(7, 60, 30, False, True) == "sweet"                       # chocolate: fat under FATTY_SHARE
    assert tc(25, 30, 10, False, False) == "savoury"
    assert tc(0, 0, 0, False, False) == "savoury"                      # no energy reads the default class


# --- R1: the ring, the share and the floor ----------------------------------------------------------------------------


def ring(host, age=AGE):
    return H(host).new(age)


def test_a_fresh_ring_is_empty(host):
    r = ring(host)
    assert r.s == AGE and r.i == 1
    assert [r.p[k] for k in range(1, 25)] == [0] * 24 and [r.a[k] for k in range(1, 25)] == [0] * 24
    assert H(host).share(r) == 0 and H(host).target(r, AGE) == 0


def test_an_eat_books_its_kcal_and_its_plain_kcal(host):
    r = ring(host)
    H(host).book(r, AGE + 0.5, 1000, True)
    H(host).book(r, AGE + 0.6, 2000, False)
    assert (r.p[1], r.a[1]) == (1000, 3000)
    assert H(host).share(r) == pytest.approx(1000 / 3000.0)
    for bad in (0, -5, float("nan"), None):
        H(host).book(r, AGE + 0.7, bad, True)
    assert (r.p[1], r.a[1]) == (1000, 3000)                             # nothing books


def test_the_share_reads_at_least_the_minimum_intake(host):
    r = ring(host)
    H(host).book(r, AGE, 300, True)
    assert H(host).share(r) == pytest.approx(300 / dv("SHARE_MIN_KCAL"))  # a little plain food is no diet of it


def test_the_ring_rotates_by_whole_hours_and_forgets_after_24(host):
    # mutation: a rotate that never moves the cursor (the share not rotating) keeps the old eat: fails here
    r = ring(host)
    H(host).book(r, AGE, 3000, True)
    H(host).rotate(r, AGE + 0.99)
    assert r.i == 1 and r.s == AGE
    H(host).rotate(r, AGE + 1.0)
    assert r.i == 2 and r.s == AGE + 1
    H(host).book(r, AGE + 5.5, 1000, False)
    assert r.i == 6 and r.a[6] == 1000
    assert H(host).share(r) == pytest.approx(0.75)
    H(host).rotate(r, AGE + 23.9)
    assert H(host).share(r) == pytest.approx(0.75)                      # the 24 hours still hold the first eat
    H(host).rotate(r, AGE + 24.0)
    assert r.p[1] == 0 and r.a[1] == 0                                  # its slot reopened
    assert H(host).share(r) == pytest.approx(0)


def test_a_long_gap_clears_the_whole_ring_at_most(host):
    r = ring(host)
    H(host).book(r, AGE, 3000, True)
    H(host).book(r, AGE + 3, 3000, True)
    H(host).rotate(r, AGE + 500.25)
    assert r.s == AGE + 500 and sum(r.a[k] for k in range(1, 25)) == 0
    assert r.i == 4                                                     # 24 steps round: every slot reopened once
    H(host).rotate(r, AGE + 400)                                        # an age behind the ring leaves it
    H(host).rotate(r, float("nan"))
    assert r.s == AGE + 500


def test_the_floor_follows_its_knots(host):
    x1, x2, y2, x3, y3 = (dv("FLOOR_KNOTS.1.1"), dv("FLOOR_KNOTS.2.1"), dv("FLOOR_KNOTS.2.2"),
                          dv("FLOOR_KNOTS.3.1"), dv("FLOOR_KNOTS.3.2"))
    f = H(host).floorOf
    assert f(0) == 0 and f(x1) == 0
    assert f(x2) == pytest.approx(y2) and f(x3) == pytest.approx(y3) and f(1.0) == pytest.approx(y3)
    assert f((x1 + x2) / 2) == pytest.approx(y2 / 2)


def test_the_writer_target_rotates_then_reads_the_floor(host):
    r = ring(host)
    H(host).book(r, AGE, 3000, True)
    assert H(host).target(r, AGE + 1) == pytest.approx(H(host).floorOf(1.0))
    assert H(host).target(r, AGE + 24) == 0                             # the plain day rolled off: it self-releases
    assert H(host).target(None, AGE) == 0


def test_the_heal(host):
    h = H(host)
    good = ring(host)
    kept, reset = h.heal(good, AGE + 1)
    assert reset is False and host.rt.eval("rawequal")(kept, good)
    fresh, reset = h.heal(None, AGE)
    assert reset is False and fresh.s == AGE
    bads = [
        "x", host.table({"s": AGE + 5, "i": 1, "p": {}, "a": {}}),
        host.table({"s": float("nan"), "i": 1}),
    ]
    for case in ({"i": 0}, {"i": 25}, {"i": 1.5}, {"i": "1"}, {"p": "x"}, {"a": None}):
        r = ring(host)
        for k, v in case.items():
            r[k] = v
        bads.append(r)
    r = ring(host)
    r.p[3] = -1
    bads.append(r)
    r = ring(host)
    r.a[24] = float("inf")
    bads.append(r)
    for b in bads:
        healed, reset = h.heal(b, AGE + 1)
        assert reset is True and healed.s == AGE + 1 and healed.a[1] == 0


# --- R2 and R3 --------------------------------------------------------------------------------------------------------


def test_prep_scales_only_a_dish_relief_by_the_cooking_level(host):
    # mutation: the sad side scaled by skill fails here
    h = H(host)
    q0, x2, q10 = dv("PREP_KNOTS.1.2"), dv("PREP_KNOTS.2.1"), dv("PREP_KNOTS.3.2")
    assert q0 < 1 < q10
    assert h.prep(-10, 0) == pytest.approx(-10 * q0)
    assert h.prep(-10, x2) == pytest.approx(-10)
    assert h.prep(-10, 10) == pytest.approx(-10 * q10)
    assert h.prep(-10, 12) == pytest.approx(-10 * q10)                 # held at the top
    assert h.prep(-10, (x2 + 10) / 2) == pytest.approx(-10 * (1 + q10) / 2)
    for v in (0, 20):
        assert h.prep(v, 0) == v and h.prep(v, 10) == v


def test_allies_scales_only_a_sad_food_while_hungry(host):
    # mutation: the happy side scaled fails here
    h = H(host)
    at = host.K.hungerCurve.THRESHOLDS[int(dv("ALLIES_LEVEL"))]
    f = dv("ALLIES_F")
    assert at == 0.25                                                   # Hungry (#0508), a strict greater-than
    assert h.allies(20, at + 0.01) == pytest.approx(20 * f)
    assert h.allies(20, at) == 20
    assert h.allies(20, 0.9) == pytest.approx(20 * f)
    for v in (-20, 0):
        assert h.allies(v, 0.9) == v


# --- R4: the taste class in monotony ----------------------------------------------------------------------------------


def test_the_class_keys(host):
    h = H(host)
    assert [h.classKey(c) for c in ("sweet", "savoury", "fatty", "staple")] == ["@sweet", "@savoury", "@fatty", "@staple"]
    assert h.classKey(None) is None and h.classKey("umami") is None


def test_monotony_books_the_class_at_its_weight(host):
    # mutation: the class weight ignored (a class booked at the whole portion) fails here
    M = host.K.monotony
    w = dv("CLASS_W")
    m = M.new()
    M.record(m, "Base.Chocolate", AGE, 1, False, "sweet")
    M.record(m, "Base.Cookie", AGE, 0.5, False, "sweet")
    assert m.t["Base.Chocolate"].n == 1 and m.t["Base.Cookie"].n == 0.5
    assert m.t["@sweet"].n == pytest.approx(1.5 * w) and m.t["@sweet"].s is None
    M.record(m, "Base.Bread", AGE, 1, True, "staple")
    assert m.t["@staple"].n == pytest.approx(w) and m.t["@staple"].s is True   # a staple class keeps the quarter weight
    M.record(m, "Base.Apple", AGE, 1, False)
    M.record(m, "Base.Pear", AGE, 1, False, "nothing")
    assert m.t["@savoury"] is None and m.t["@fatty"] is None              # no class, or no such class: no key


def test_a_rotation_of_one_class_holds_the_class_level(host):
    M = host.K.monotony
    w = dv("CLASS_W")
    m = M.new()
    sweets = ["Base.S%d" % k for k in range(60)]
    for k, t in enumerate(sweets):
        M.record(m, t, AGE, 1, False, "sweet")
    u, _ = M.target(m, AGE)
    want = min(dial_value("monotony.CAP"), dial_value("monotony.SLOPE") * (60 * w - 1))
    assert u == pytest.approx(want)                                      # each food once: only the class holds
    healed, reset = M.heal(m, AGE)
    assert reset is False                                                # a class key is a string key the heal keeps


def test_the_record_shape_reaches_the_store_and_the_resume(host):
    K = host.K
    assert "hedonics.s" in list(K.resume.STAMPS.values())
    assert "hedonics" in list(K.store.INPUTS.values())
    rec = host.table({"lastSeen": AGE})
    rec.hedonics = ring(host, AGE)
    K.resume.resume(rec, AGE + 10.5)
    assert rec.hedonics.s == AGE + 10.5                                  # moved past the absence: no hour rolls off


def test_the_kernel_reads_no_java_and_states_rule_6():
    with open(KERNEL, encoding="utf-8") as fh:
        src = fh.read()
    assert "never per tick (Rule 6)" in src and "nothing is allocated after" in src
