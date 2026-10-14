"""The weight band, the direction flags, the macro-mirror maps, the trailing-24 h window and the record calendar
(NR_Kernel_Body.lua), Plan 3 Task 6. The band-anchored weight split (split, interp and their tables, the build
offsets) and the old constructor are removed in Plan 13 Task 12: the body is K.body.new over K.body.create
(test_body_create.py).

NR_Kernel_Body.lua is a kernel file (its name is NR_Kernel*), so the session `host` fixture loads it
through its glob and already has NutritionRevamp.kernel.body. Every expectation below is hand-computed
from the file's constants: the band edges (#0531, #0155), the flag thresholds (ruling 17) and the mirror maps
(#0022, #0023, ruling 13).
"""
import pytest

TOL = 1e-9


def _close(a, b):
    return abs(a - b) < TOL


# --- constants ---

def test_constants(host):
    b = host.K.body
    assert b.WEEK_N == 7
    # Plan 13 Task 12 (spec section 9.2): the weight split and its tables are gone, and so is newLean (renamed new)
    for name in ("split", "interp", "ANCHORS_W", "BF_MALE", "BF_FEMALE", "BF_MIN", "BF_MAX", "BUILD_OFFSET",
                 "BUILD_KEYS", "KNOTS", "W_MIN", "W_MAX", "newLean"):
        assert b[name] is None, name


# --- effSex (Plan 13 Task 3) ---

def test_eff_sex_is_male_unless_the_option_is_on(host):
    assert host.call("body.effSex", 2, False) == 1
    assert host.call("body.effSex", 2, True) == 2
    assert host.call("body.effSex", 1, True) == 1
    assert host.call("body.effSex", 1, False) == 1
    assert host.call("body.effSex", 2, None) == 1


# --- band ---

@pytest.mark.parametrize("w,band", [
    (100, "obese"),
    (130, "obese"),
    (99.99, "overweight"),
    (85, "overweight"),
    (84.99, "normal"),
    (80, "normal"),
    (75.01, "normal"),
    (75, "underweight"),
    (65.01, "underweight"),
    (65, "veryUnderweight"),
    (50.01, "veryUnderweight"),
    (50, "emaciated"),
    (30, "emaciated"),
])
def test_band(host, w, band):
    assert host.call("body.band", w) == band


# --- flags / trend ---

@pytest.mark.parametrize("t,expect", [
    (0.05, (True, False, False)),
    (0.15, (True, True, False)),
    (-0.05, (False, False, True)),
    (0, (False, False, False)),
    (0.02, (False, False, False)),
    (0.10, (True, False, False)),
    (-0.02, (False, False, False)),
])
def test_flags(host, t, expect):
    assert tuple(host.call("body.flags", t)) == expect


def test_trend_reads_the_oldest_slot(host):
    ring = host.table({i: 80 for i in range(1, 8)})
    assert _close(host.call("body.trend", ring, 80.7), 0.1)
    ring[1] = 81.4
    assert _close(host.call("body.trend", ring, 80.7), -0.1)


def test_trend_of_a_fresh_ring_is_zero(host):
    ring = host.table({i: 72.5 for i in range(1, 8)})
    assert host.call("body.trend", ring, 72.5) == 0


# --- the macro-mirror maps ---

@pytest.mark.parametrize("eb,out", [(5000, 3700), (-3000, -2200), (120.5, 120.5), (3700, 3700), (-2200, -2200)])
def test_map_calories(host, eb, out):
    assert _close(host.call("body.mapCalories", eb), out)


@pytest.mark.parametrize("p,out", [
    (0.3, -400),
    (0.5, -400),
    (0.65, -150),
    (0.8, 0),
    (1.2, 75),
    (1.6, 150),
    (2.0, 200),
])
def test_map_proteins(host, p, out):
    assert _close(host.call("body.mapProteins", p), out)


def test_map_proteins_opens_the_xp_arm_near_107(host):
    # #2112: vanilla's x1.5 XP arm needs 50 < proteins < 300; 1.07 g/kg/d maps to 50.625.
    v = host.call("body.mapProteins", 1.07)
    assert v >= 50
    assert _close(v, 50.625)


@pytest.mark.parametrize("g,out", [(400, 100), (300, 0), (0, -300), (2000, 1000), (-1000, -500)])
def test_map_carbs(host, g, out):
    assert _close(host.call("body.mapCarbs", g), out)


@pytest.mark.parametrize("g,out", [(0, -70), (70, 0), (120, 50), (5000, 1000)])
def test_map_lipids(host, g, out):
    assert _close(host.call("body.mapLipids", g), out)


# --- new ---

def test_new_rings_are_distinct_tables(host):
    spec = host.call("body.create", "FEEBLE", "OVERWEIGHT", host.K.strength.DEFAULTS, 2)
    body = host.K.body["new"](spec, 2, 47.5)
    week = body.bandWeek
    assert not host.rt.eval("rawequal")(week[1], week[2])
    assert not host.rt.eval("rawequal")(body.sig7, body.eb7)
    week[1][1] = 5
    assert week[2][1] == 0
    py = host.py(body)
    assert py["dayIndex"] == 1 and py["wday"] == 1


# --- the trailing-24 h window (Plan 11d Task 9c, ruling C-8) ---

KEYS = ("kcal", "ee", "ex", "p", "carb", "lip")


def _ring(t, key):
    return [t[key][i] for i in range(1, 26)]


def test_trail_constants(host):
    b = host.K.body
    assert b.TRAIL_N == 25
    assert list(host.py(b.TRAIL_KEYS).values()) == list(KEYS)


def test_new_trail_is_empty_and_unbuilt(host):
    t = host.K.body.newTrail(100.25)
    assert t.at == 100.25 and t.ch == -1
    for k in KEYS:
        assert _ring(t, k) == [0] * 25, k
        assert len(host.py(t[k])) == 25, k
        assert t.c[k] == 0, k
    assert not host.rt.eval("rawequal")(t.kcal, t.ee)


def test_trail_slot_is_the_hour_modulo_the_ring(host):
    s = host.K.body.trailSlot
    assert [s(h) for h in (0, 1, 24, 25, 26, 100)] == [1, 2, 25, 1, 2, 1]


def test_trail_add_books_the_current_hour(host):
    b = host.K.body
    t = b.newTrail(100.5)
    b.trailAdd(t, "kcal", 300.0)
    b.trailAdd(t, "kcal", 50.0)
    b.trailAdd(t, "ee", 2.0)
    assert t.kcal[b.trailSlot(100)] == 350.0 and t.ee[b.trailSlot(100)] == 2.0
    assert sum(_ring(t, "kcal")) == 350.0


def test_trail_to_zeroes_each_hour_the_clock_passes(host):
    b = host.K.body
    t = b.newTrail(0.5)
    for h in range(25):
        b.trailTo(t, h + 0.5)
        b.trailAdd(t, "ee", float(h + 1))
    assert _ring(t, "ee") == [float(h + 1) for h in range(25)]
    b.trailTo(t, 26.25)                                  # hours 25 and 26 pass: their slots (1 and 2) are zeroed
    assert _ring(t, "ee")[:2] == [0, 0] and _ring(t, "ee")[2:] == [float(h + 1) for h in range(2, 25)]
    assert t.at == 26.25


def test_trail_to_within_the_hour_or_backwards_zeroes_nothing(host):
    b = host.K.body
    t = b.newTrail(10.1)
    b.trailAdd(t, "p", 30.0)
    b.trailTo(t, 10.9)
    assert t.p[b.trailSlot(10)] == 30.0 and t.at == 10.9
    b.trailTo(t, 9.0)                                    # behind the window: left as it is
    assert t.p[b.trailSlot(10)] == 30.0 and t.at == 10.9
    b.trailTo(t, float("nan"))
    assert t.at == 10.9


def test_trail_to_a_gap_longer_than_the_ring_empties_it(host):
    b = host.K.body
    t = b.newTrail(5.5)
    for k in KEYS:
        for i in range(1, 26):
            t[k][i] = 7.0
    b.trailTo(t, 5.5 + 1000)
    for k in KEYS:
        assert _ring(t, k) == [0] * 25, k


def test_trail_shift_carries_the_window_forward_with_its_contents(host):
    # Plan 12 A1: an offline gap is skipped, so the window moves to the start of the integrated step with every slot
    # keeping its age behind the window's hour, and the closed sums rebuild at the next read
    b = host.K.body
    t = b.newTrail(76.0)
    b.trailAdd(t, "ex", 240.0)
    for h in range(77, 101):
        b.trailTo(t, float(h))
        b.trailAdd(t, "ex", float(h))
    t.at = 100.5
    before = b.trail24(t, "ex")
    b.trailShift(t, 100.5 + 71.75)                       # 71.75 h skipped: the hour moves from 100 to 172
    assert t.at == 172.25 and t.ch == -1
    for back in range(25):
        assert t.ex[b.trailSlot(172 - back)] == ([240.0] + [float(h) for h in range(77, 101)])[24 - back], back
    b.trailTo(t, 172.5)
    assert _close(b.trail24(t, "ex"), before)


def test_trail_shift_backwards_or_in_place_moves_nothing(host):
    b = host.K.body
    t = b.newTrail(10.5)
    b.trailAdd(t, "p", 30.0)
    b.trailShift(t, 10.5)
    b.trailShift(t, 9.0)
    b.trailShift(t, float("nan"))
    assert t.at == 10.5 and t.p[b.trailSlot(10)] == 30.0 and _ring(t, "p").count(0) == 24


def test_trail24_weights_the_oldest_hour_by_its_share_still_inside(host):
    # slots: hour 100 (current) 5, hour 76 (the oldest, H - 24) 240, the 23 hours between 10 each; at 100.25 the
    # window is the current 5, the 23 x 10 and three quarters of the oldest
    b = host.K.body
    t = b.newTrail(76.0)
    b.trailAdd(t, "ex", 240.0)
    for h in range(77, 100):
        b.trailTo(t, float(h))
        b.trailAdd(t, "ex", 10.0)
    b.trailTo(t, 100.25)
    b.trailAdd(t, "ex", 5.0)
    assert _close(b.trail24(t, "ex"), 5 + 230 + 0.75 * 240)
    assert t.ch == 100 and _close(t.c.ex, 230 + 240)
    b.trailTo(t, 100.75)                                 # the same hour: the closed sums are kept
    assert _close(b.trail24(t, "ex"), 5 + 230 + 0.25 * 240)
    b.trailTo(t, 101.0)                                  # the hour turns: hour 76's slot becomes hour 101's
    assert _close(b.trail24(t, "ex"), 5 + 230)
    assert t.ch == 101


def test_trail24_rebuilds_closed_sums_built_for_another_hour(host):
    b = host.K.body
    t = b.newTrail(3.5)
    b.trailAdd(t, "lip", 20.0)
    t.ch = 3
    t.c.lip = 999.0                                      # a stale sum for the current hour is trusted ...
    assert _close(b.trail24(t, "lip"), 999.0 + 20.0)
    t.ch = -1                                            # ... and rebuilt when it was built for another hour
    assert _close(b.trail24(t, "lip"), 20.0)
    assert t.c.lip == 0


def test_a_steady_rate_reads_a_full_day_at_every_minute(host):
    # one unit a minute for two days: from the second day on the window reads 1440 at every minute (the oldest hour
    # spread evenly, as the interpolation assumes)
    b = host.K.body
    t = b.newTrail(0.0)
    worst = 0.0
    for m in range(1, 2 * 1440 + 1):
        b.trailTo(t, m / 60)
        b.trailAdd(t, "ee", 1.0)
        if m > 1440:
            worst = max(worst, abs(b.trail24(t, "ee") - 1440))
    assert worst < 1.0 + 1e-9, worst


def test_trail_intake_books_the_four_macros_of_a_vector(host):
    b = host.K.body
    t = b.newTrail(7.5)
    b.trailIntake(t, host.table(dict(calories=600.0, proteins=30.0, carbs=70.0, lipids=20.0, fibre=5.0)))
    s = b.trailSlot(7)
    assert (t.kcal[s], t.p[s], t.carb[s], t.lip[s], t.ee[s], t.ex[s]) == (600.0, 30.0, 70.0, 20.0, 0, 0)


# --- the window's minors (Plan 11d Task 9d; the Task 9c review) ---

def test_trail_closed_returns_the_count_of_slots_it_zeroed(host):
    # a rebuild zeroes every non-finite slot of every ring, the current hour's too, and returns the closed sums and
    # the count it zeroed; a call that finds the sums built for the hour rebuilds nothing and zeroes none
    b = host.K.body
    t = b.newTrail(100.5)
    t.ee[b.trailSlot(90)] = float("nan")
    t.ee[b.trailSlot(91)] = float("inf")
    t.kcal[b.trailSlot(100)] = float("-inf")
    t.p[b.trailSlot(95)] = 12.0
    c, n = b.trailClosed(t)
    assert n == 3 and t.ch == 100
    assert t.ee[b.trailSlot(90)] == 0 and t.ee[b.trailSlot(91)] == 0 and t.kcal[b.trailSlot(100)] == 0
    assert c.p == 12.0 and c.ee == 0
    t.ee[b.trailSlot(92)] = float("nan")
    c, n = b.trailClosed(t)
    assert n == 0 and t.ee[b.trailSlot(92)] != t.ee[b.trailSlot(92)]


def test_trail_ring_sum_sums_all_but_the_current_slot_and_counts_what_it_zeroed(host):
    b = host.K.body
    t = b.newTrail(0.0)
    for i in range(1, 26):
        t.lip[i] = float(i)
    t.lip[4] = float("nan")
    s, z = b.trailRingSum(t.lip, 2)
    assert z == 1 and t.lip[4] == 0
    assert s == sum(range(1, 26)) - 2 - 4


# --- the record calendar (Plan 13 Task 4, ruling 13-5) ---

def test_calendar_closes_once_on_a_new_world_day(host):
    b = host.table({"wday": 5, "dayIndex": 5})
    assert host.call("body.calendar", b, 5 * 24 + 23.9, False) == 0
    assert host.call("body.calendar", b, 6 * 24 + 0.1, False) == 1
    assert b["wday"] == 6 and b["dayIndex"] == 5
    assert host.call("body.calendar", b, 6 * 24 + 0.2, False) == 0   # the new world day closes once


def test_calendar_closes_nothing_after_a_gap(host):
    b = host.table({"wday": 5, "dayIndex": 5})
    assert host.call("body.calendar", b, 9 * 24 + 3.0, True) == 0
    assert b["wday"] == 9 and b["dayIndex"] == 5
    assert host.call("body.calendar", b, 9 * 24 + 23.0, False) == 0  # the day open at departure continues
    assert host.call("body.calendar", b, 10 * 24 + 0.05, False) == 1


def test_calendar_closes_at_most_one_day_a_minute(host):
    b = host.table({"wday": 5, "dayIndex": 5})
    assert host.call("body.calendar", b, 8 * 24 + 0.5, False) == 1
    assert b["wday"] == 8 and b["dayIndex"] == 5
    assert host.call("body.calendar", b, 8 * 24 + 0.6, False) == 0


def test_calendar_after_a_gap_restamps_a_behind_world_day(host):
    b = host.table({"wday": 9, "dayIndex": 5})
    assert host.call("body.calendar", b, 9 * 24 + 1.0, True) == 0
    assert b["wday"] == 9
