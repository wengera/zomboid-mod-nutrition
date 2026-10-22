"""Monotony as a self-releasing floor (Plan 11e Task 3, ruling 11e-1; Plan 11f Task 9b, rulings T9-1, T9-3).

A per-player record of recent eats by full type, record.monotony = { t = { [fullType] = { n, last, s } } }: n is the
decayed count of meal-sized portions (ruling T3-3: each eat weighs w = min(1, kcal / MEAL_KCAL)) at world age
`last`, decaying with a 3-day half-life, s marks a staple; an entry whose last eat is beyond the 7-day window counts 0 once its decayed count is one portion or less (Plan 11f Task 9b fix 1: no step at the window edge).
A type's level is f x min(CAP, SLOPE x max(0, n - 1)) (f STAPLE for a staple), the target the most repeated type's
level, the same on UNHAPPINESS and BOREDOM, BOREDOM's held under BORED_MAX. Hand-computed from the constants.
"""
import math
import os
import re

import pytest

from .conftest import dial_line

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
KERNEL = os.path.join(SHARED, "NR_Kernel_Monotony.lua")

AGE = 1000.0
DAY = 24.0


def M(host):
    return host.K.monotony


def decay(dt):
    return 2 ** (-dt / 72.0)


def test_the_constants(host):
    m = M(host)
    assert (m.WINDOW_H, m.HALF_LIFE_H, m.SLOPE, m.CAP, m.STAPLE) == (168, 72, 4.3, 30, 0.25)
    assert m.MEAL_KCAL == 400
    assert m.BORED_MAX == 49


def test_each_constant_names_its_rows_and_its_label():
    with open(KERNEL, encoding="utf-8") as fh:
        src = fh.read()
    for name in ("WINDOW_H", "HALF_LIFE_H", "SLOPE", "CAP", "STAPLE"):
        line = dial_line("monotony." + name)                            # Plan 19: the provenance is the registry row's
        assert "game choice, Plan 11e (ruling 11e-1)" in line, name
    assert "#0042" in dial_line("monotony.SLOPE")
    assert "#0042" in dial_line("monotony.CAP")
    for row in ("S1592", "S1593", "S1594", "S1595", "S1596", "S1597"):
        assert row in src, row
    assert "free choice" in src                                         # S1594: the player choosing variety
    meal = dial_line("monotony.MEAL_KCAL")
    assert "game choice, Plan 11e (ruling T3-3); the studies' unit is a served portion (S1592-S1595)" in meal
    window = dial_line("monotony.WINDOW_H")
    assert "measured from the type's latest eat; a type eaten daily keeps its decayed older eats" in window
    cap = dial_line("monotony.CAP")
    for want in ("Angus 2026-10-11", "level-1 moodles", "S1592", "S1597", "direction, not size", "#2369",
                 "Moodle.Update", "no longer binds the cap"):
        assert want in cap, want
    bored = dial_line("monotony.BORED_MAX")
    assert "#2369" in bored and "UpdateBoredom @510-@575" in bored and "ruling T9-3" in bored


def test_the_kernel_says_it_is_a_self_releasing_floor_and_names_the_panic_wipe():
    with open(KERNEL, encoding="utf-8") as fh:
        src = fh.read()
    assert "self-releasing floor" in src
    assert "PANIC > 5" in dial_line("monotony.BORED_MAX") and "T9-3" in src
    assert "delta" not in re.sub(r"--[^\n]*", "", src)                 # the add at the eat is gone (ruling T9-1)


def test_new_is_an_empty_type_map(host):
    m = M(host).new()
    assert host.py(m) == {"t": {}}


# --- a type's level and the target ---------------------------------------------------------------------------


def tgt(host, m, age):
    return M(host).target(m, age)


def test_an_empty_record_targets_nothing(host):
    assert tgt(host, M(host).new(), AGE) == (0, 0)


def test_the_first_portion_of_a_type_targets_nothing(host):
    m = M(host).new()
    M(host).record(m, "Base.Apple", AGE, 1, False)
    assert tgt(host, m, AGE) == (0, 0)


def test_repeats_raise_the_level_by_the_slope_per_recent_portion(host):
    m = M(host).new()
    got = []
    for i in range(4):
        M(host).record(m, "Base.Apple", AGE, 1, False)
        got.append(tgt(host, m, AGE)[0])
    assert got == pytest.approx([0, 4.3, 8.6, 12.9])


def test_both_stats_take_the_same_target_under_the_bound(host):
    m = M(host).new()
    M(host).record(m, "Base.Apple", AGE, 1, False)
    M(host).record(m, "Base.Apple", AGE, 1, False)
    u, b = tgt(host, m, AGE)
    assert u == b == pytest.approx(4.3)


def test_the_fifth_daily_portion_holds_about_a_stale_item(host):
    # the anchor (#0042): one portion a day, right after the fifth the level reads
    # 4.3 x (2^-1/3 + 2^-2/3 + 2^-1 + 2^-4/3) = 9.978, vanilla's stale +10, now held as a floor, not added
    m = M(host).new()
    for d in range(5):
        M(host).record(m, "Base.Apple", AGE + d * DAY, 1, False)
    u, _ = tgt(host, m, AGE + 4 * DAY)
    want = 4.3 * sum(decay(k * DAY) for k in range(1, 5))
    assert u == pytest.approx(want, rel=1e-12)
    assert u == pytest.approx(9.978, abs=1e-3)


def test_the_level_follows_the_decaying_count(host):
    m = M(host).new()
    for _ in range(3):
        M(host).record(m, "Base.Apple", AGE, 1, False)
    assert tgt(host, m, AGE)[0] == pytest.approx(4.3 * 2)
    assert tgt(host, m, AGE + 72)[0] == pytest.approx(4.3 * (3 * 0.5 - 1))     # the count's half-life
    assert tgt(host, m, AGE + 144)[0] == 0                                   # n 0.75: under one portion


def test_past_the_window_a_type_fades_with_its_count_and_takes_no_step(host):
    # Plan 11f Task 9b fix 1: the window no longer cuts a level above 0; the type counts 0 past the window only once
    # its decayed count is one portion or less, where its level is already 0
    m = M(host).new()
    for _ in range(10):
        M(host).record(m, "Base.Apple", AGE, 1, False)
    assert tgt(host, m, AGE + 168)[0] == pytest.approx(4.3 * (10 * decay(168) - 1))
    assert tgt(host, m, AGE + 168.01)[0] == pytest.approx(4.3 * (10 * decay(168.01) - 1))
    one = 72 * math.log2(10)                                          # n falls to one portion: 239.2 h
    assert tgt(host, m, AGE + one - 1)[0] == pytest.approx(4.3 * (10 * decay(one - 1) - 1))
    assert tgt(host, m, AGE + one + 0.01) == (0, 0)
    assert M(host).count(m.t["Base.Apple"], AGE + one - 1) == pytest.approx(10 * decay(one - 1))
    assert M(host).count(m.t["Base.Apple"], AGE + one + 0.01) == 0


def test_inside_the_window_a_count_under_one_portion_still_counts(host):
    m = M(host).new()
    M(host).record(m, "Base.Apple", AGE, 1, False)
    assert M(host).count(m.t["Base.Apple"], AGE + 167) == pytest.approx(decay(167))
    assert M(host).count(m.t["Base.Apple"], AGE + 169) == 0


def test_a_staple_holds_a_quarter_of_the_level_also_at_the_cap(host):
    m = M(host).new()
    s = M(host).new()
    for _ in range(3):
        M(host).record(m, "Base.Apple", AGE, 1, False)
        M(host).record(s, "Base.Bread", AGE, 1, True)
    assert tgt(host, s, AGE)[0] == pytest.approx(0.25 * tgt(host, m, AGE)[0])
    for _ in range(20):
        M(host).record(m, "Base.Apple", AGE, 1, False)
        M(host).record(s, "Base.Bread", AGE, 1, True)
    assert tgt(host, m, AGE)[0] == 30 and tgt(host, s, AGE)[0] == pytest.approx(7.5)


def test_the_cap_holds(host):
    m = M(host).new()
    for _ in range(10):
        M(host).record(m, "Base.Apple", AGE, 1, False)
    assert tgt(host, m, AGE) == (30, 30)


def test_the_most_repeated_type_sets_the_target(host):
    # the composition inside monotony: the maximum over types, so a rotation of k foods reads the level of one food
    # eaten a k-th as often, and the most repeated food is what the character is tired of
    m = M(host).new()
    for _ in range(3):
        M(host).record(m, "Base.Apple", AGE, 1, False)
    for _ in range(2):
        M(host).record(m, "Base.Orange", AGE, 1, False)
    assert tgt(host, m, AGE)[0] == pytest.approx(8.6)
    M(host).record(m, "Base.Bread", AGE, 1, True)
    assert tgt(host, m, AGE)[0] == pytest.approx(8.6)


def test_types_are_counted_apart(host):
    m = M(host).new()
    M(host).record(m, "Base.Apple", AGE, 1, False)
    M(host).record(m, "Base.Orange", AGE, 1, False)
    assert tgt(host, m, AGE) == (0, 0)


def test_the_boredom_target_stays_under_the_bored_level_2_step_whatever_the_cap(host):
    # ruling T9-3: vanilla adds UNHAPPINESS while the BORED moodle is above level 1, from BOREDOM above 50 (#2369,
    # UpdateBoredom @510-@575), so monotony's BOREDOM target is held at 49 even if the cap is raised
    k = M(host)
    cap = k.CAP
    try:
        k.CAP = 1000
        m = k.new()
        for _ in range(30):
            k.record(m, "Base.Apple", AGE, 1, False)
        u, b = tgt(host, m, AGE)
        assert u == pytest.approx(4.3 * 29) and b == 49
    finally:
        k.CAP = cap
    assert k.CAP == 30


def test_a_partial_eat_counts_its_share(host):
    m = M(host).new()
    M(host).record(m, "Base.Apple", AGE, 1, False)
    M(host).record(m, "Base.Apple", AGE, 0.5, False)
    assert m.t["Base.Apple"].n == pytest.approx(1.5)
    assert tgt(host, m, AGE)[0] == pytest.approx(4.3 * 0.5)


def test_an_item_eaten_in_parts_is_not_monotonous_against_itself(host):
    m = M(host).new()
    for _ in range(4):
        M(host).record(m, "Base.Apple", AGE, 0.25, False)
        assert tgt(host, m, AGE)[0] == 0
    assert m.t["Base.Apple"].n == pytest.approx(1.0)


def test_a_nil_share_is_one_and_a_share_is_clamped(host):
    m = M(host).new()
    M(host).record(m, "Base.Apple", AGE)
    assert m.t["Base.Apple"].n == 1
    M(host).record(m, "Base.Apple", AGE, 3)
    assert m.t["Base.Apple"].n == 2
    M(host).record(m, "Base.Apple", AGE, -1)
    assert m.t["Base.Apple"].n == 2


def test_record_decays_the_count_to_the_eat_and_stamps_it(host):
    m = M(host).new()
    M(host).record(m, "Base.Apple", AGE, 1, False)
    e = M(host).record(m, "Base.Apple", AGE + 72, 1, False)
    assert e.n == pytest.approx(1.5) and e.last == AGE + 72
    e = M(host).record(m, "Base.Apple", AGE + 72 + 169, 1, False)
    assert e.n == 1 and e.last == AGE + 72 + 169                         # past the window: a fresh count


def test_record_marks_a_staple_and_only_a_staple(host):
    m = M(host).new()
    M(host).record(m, "Base.Bread", AGE, 1, True)
    M(host).record(m, "Base.Apple", AGE, 1, False)
    M(host).record(m, "Base.Pear", AGE, 1)
    assert host.py(m.t) == {"Base.Bread": {"n": 1, "last": AGE, "s": True}, "Base.Apple": {"n": 1, "last": AGE},
                            "Base.Pear": {"n": 1, "last": AGE}}
    M(host).record(m, "Base.Bread", AGE, 1, False)                      # the latest eat's reading stands
    assert m.t["Base.Bread"].s is None


def test_count_of_no_entry_is_zero(host):
    assert M(host).count(None, AGE) == 0


# --- the portion weight (ruling T3-3): an eat counts its kcal over a 400 kcal meal, at most one ----------------


@pytest.mark.parametrize("kcal,w", [(400, 1), (800, 1), (200, 0.5), (5, 0.0125), (100.0, 0.25)])
def test_the_weight_is_the_kcal_over_a_meal_at_most_one(host, kcal, w):
    assert M(host).weightOf(kcal) == pytest.approx(w)


@pytest.mark.parametrize("raw", ["0", "-50", "nil", "0 / 0", "1 / 0", "'x'"])
def test_no_energy_or_unreadable_energy_weighs_nothing(host, raw):
    assert M(host).weightOf(host.rt.eval(raw)) == 0


def test_ten_small_items_in_one_sitting_target_nothing(host):
    # ten 5 kcal items (insects, a sugar packet): 0.125 of a meal in all, so no repeat of a portion yet
    m = M(host).new()
    for _ in range(10):
        M(host).record(m, "Base.Grasshopper", AGE, M(host).weightOf(5), False)
    assert tgt(host, m, AGE) == (0, 0)
    assert m.t["Base.Grasshopper"].n == pytest.approx(0.125)


def _daily(host, kcal, days):
    m = M(host).new()
    w = M(host).weightOf(kcal)
    for d in range(days):
        M(host).record(m, "Base.Apple", AGE + d * DAY, w, False)
    return m, tgt(host, m, AGE + (days - 1) * DAY)[0]


def test_a_200_kcal_item_daily_counts_half_as_fast_as_a_400_one(host):
    m400, d400 = _daily(host, 400, 5)
    m200, d200 = _daily(host, 200, 5)
    assert m200.t["Base.Apple"].n == pytest.approx(0.5 * m400.t["Base.Apple"].n)
    assert d400 == pytest.approx(9.978, abs=1e-3)                      # the anchor holds for a meal-sized eat
    s5 = sum(decay(k * DAY) for k in range(5))
    assert d200 == pytest.approx(4.3 * (0.5 * s5 - 1), rel=1e-12)       # the half weight halves the count
    _, d800 = _daily(host, 800, 5)
    assert d800 == pytest.approx(d400)                                 # a portion past a meal still weighs one


# --- pruning -------------------------------------------------------------------------------------------------


def test_prune_drops_only_the_types_beyond_the_window(host):
    m = M(host).new()
    M(host).record(m, "Base.Old", AGE - 169, 1)
    M(host).record(m, "Base.Older", AGE - 300, 1)
    M(host).record(m, "Base.Edge", AGE - 168, 1)
    M(host).record(m, "Base.New", AGE, 1)
    assert M(host).prune(m, AGE) == 2
    assert sorted(host.py(m.t)) == ["Base.Edge", "Base.New"]


def test_prune_keeps_a_type_past_the_window_until_its_count_falls_to_one_portion(host):
    # Plan 11f Task 9b fix 1: the prune drops only a type whose level is already 0, so it never takes a step
    m = M(host).new()
    for _ in range(10):
        M(host).record(m, "Base.Heavy", AGE - 169, 1, False)
    M(host).record(m, "Base.Old", AGE - 169, 1, False)
    assert M(host).prune(m, AGE) == 1
    assert list(host.py(m.t)) == ["Base.Heavy"]
    one = AGE - 169 + 72 * math.log2(10)
    assert M(host).prune(m, one - 0.01) == 0
    assert M(host).prune(m, one + 0.01) == 1
    assert host.py(m.t) == {}


def test_prune_of_a_recent_record_removes_nothing(host):
    m = M(host).new()
    assert M(host).prune(m, AGE) == 0
    M(host).record(m, "Base.New", AGE, 1)
    assert M(host).prune(m, AGE) == 0
    assert list(host.py(m.t)) == ["Base.New"]


# --- staples: the food data's FoodType, and the named potato and oat types it misses ---------------------------


@pytest.mark.parametrize("full,ft", [("Base.Bread", "Bread"), ("Base.Rice", "Rice"), ("Base.Pasta", "Pasta"),
                                     ("Mod.Loaf", "Bread"), ("Base.Potato", "Vegetables"), ("Base.OatsRaw", None),
                                     ("Base.Oatmeal", None), ("Base.CannedPotato_Open", "Vegetables"),
                                     ("Base.Toast", None), ("Base.BagelPlain", None), ("Base.Tortilla", None),
                                     ("Base.Cornbread", "NoExplicit"), ("Base.WaterPotPasta", None),
                                     ("Base.WaterPotForgedPasta", None), ("Base.WaterSaucepanPasta", None),
                                     ("Base.WaterSaucepanPastaCopper", None)])
def test_staples(host, full, ft):
    assert M(host).isStaple(full, ft) is True


@pytest.mark.parametrize("full,ft", [("Base.Apple", "Fruits"), ("Base.Carrots", "Vegetables"), ("Base.Steak", "Beef"),
                                     ("Base.Cereal", None), ("Base.Sandwich", None), ("Base.Chocolate", "Chocolate")])
def test_non_staples(host, full, ft):
    assert M(host).isStaple(full, ft) is False


# --- the heal: a corrupt table resets -----------------------------------------------------------------------


def test_heal_lays_a_fresh_table_when_absent_and_counts_nothing(host):
    m, healed = M(host).heal(None, AGE)
    assert host.py(m) == {"t": {}} and healed is False


def test_heal_keeps_a_sound_table(host):
    m = M(host).new()
    M(host).record(m, "Base.Apple", AGE, 1, False)
    M(host).record(m, "Base.Bread", AGE, 1, True)
    out, healed = M(host).heal(m, AGE)
    assert host.rt.eval("rawequal")(out, m) and healed is False
    out, healed = M(host).heal(host.rt.eval("{ t = { ['Base.A'] = { n = 1, last = 0, s = false } } }"), AGE)
    assert healed is False


@pytest.mark.parametrize("raw", ["'junk'", "7", "{ t = 'x' }", "{ }", "{ t = { ['Base.A'] = 3 } }",
                                 "{ t = { [4] = { n = 1, last = 0 } } }",
                                 "{ t = { ['Base.A'] = { n = 0 / 0, last = 0 } } }",
                                 "{ t = { ['Base.A'] = { n = 1, last = 1 / 0 } } }",
                                 "{ t = { ['Base.A'] = { n = 'x', last = 0 } } }",
                                 "{ t = { ['Base.A'] = { n = -1, last = 0 } } }",
                                 "{ t = { ['Base.A'] = { n = 1, last = 2000 } } }",
                                 "{ t = { ['Base.A'] = { n = 1, last = 0, s = 'yes' } } }",
                                 "{ t = { ['Base.A'] = { n = 1, last = 0 }, ['Base.B'] = { last = 0 } } }"])
def test_heal_resets_a_corrupt_table_and_says_so(host, raw):
    m, healed = M(host).heal(host.rt.eval(raw), AGE)
    assert host.py(m) == {"t": {}} and healed is True


def test_the_kernel_never_names_hunger():
    with open(KERNEL, encoding="utf-8") as fh:
        code = "\n".join(l.split("--")[0] for l in fh.read().splitlines())
    assert "HUNGER" not in code.upper().replace("HUNGER_", "")


# --- the floor oracles (Plan 11f Task 9b): the kernel's target through K.hybrid.write, minute by minute ----------
# The writer's composition for a character with no other mood source: UNHAPPINESS and BOREDOM raised toward
# K.monotony.target at the hybrid's rise rates and released by the target's fall (#3119). Vanilla's own BOREDOM moves
# and the PANIC wipe are not modelled: the reading is the floor alone.

MEALS_3 = (8 * 60, 13 * 60, 19 * 60)            # minutes of the day


def floor_run(host, plan, days, start_u=0.0, start_b=0.0):
    """plan(day, minute) -> (fullType, staple) or None. Returns per-minute (age, u, b, tu, tb)."""
    k = host.K
    m = k.monotony.new()
    inp, out, c = k.hybrid.input(), k.hybrid.output(), k.hybrid.defaults()
    u, b, lu, lb = start_u, start_b, 0.0, 0.0
    rows = []
    for i in range(days * 1440):
        day, minute = divmod(i, 1440)
        age = AGE + i / 60.0
        eat = plan(day, minute)
        if eat is not None:
            k.monotony.record(m, eat[0], age, 1, eat[1])
        tu, tb = k.monotony.target(m, age)
        inp.dtS, inp.unhappy, inp.unhappyTarget, inp.lastUnhappyTarget = 60, u, tu, lu
        inp.bored, inp.boredTarget, inp.lastBoredTarget = b, tb, lb
        k.hybrid.write(inp, out, c)
        if out.unhappy is not None:
            u = out.unhappy
        if out.bored is not None:
            b = out.bored
        lu, lb = out.unhappyTarget, out.boredTarget
        rows.append((age, u, b, tu, tb))
    return rows


def one_food(full, staple):
    def plan(day, minute):
        return (full, staple) if minute in MEALS_3 else None
    return plan


@pytest.fixture(scope="module")
def mono14(host):
    return floor_run(host, one_food("Base.Apple", False), 14)


def test_a_one_food_diet_rises_to_a_bounded_floor_and_never_exceeds_it(mono14):
    peak_u = max(r[1] for r in mono14)
    peak_b = max(r[2] for r in mono14)
    assert peak_u == pytest.approx(30) and peak_b == pytest.approx(30)
    first = next(i for i, r in enumerate(mono14) if r[1] >= 30 - 1e-9)
    assert first // 1440 == 3                                        # reached on day 3 (the twelfth portion, 19:00)
    assert all(abs(r[1] - 30) < 1e-9 and abs(r[2] - 30) < 1e-9 for r in mono14[5 * 1440:])


def test_a_one_food_diet_alone_shows_the_level_1_unhappy_and_bored_moodles(mono14):
    # Angus 2026-10-11: monotony alone reaches the level-1 moodles. Moodle.Update sets a level when the stat is
    # strictly above its threshold (fcmpl/ifle, 42.21): UNHAPPY 20 and BORED 25 for level 1, BORED 50 for level 2
    # (#2369); the steady floor clears level 1 by a margin and stays under BORED level 2
    steady = mono14[5 * 1440:]
    assert all(r[1] > 20 + 5 and r[2] > 25 + 4 for r in steady)
    assert all(r[2] < 50 for r in mono14)
    assert all(r[1] > 25 for r in mono14[4 * 1440 + 8 * 60 + 30:])   # from day 4's breakfast on, both above level 1


def test_the_floor_follows_the_target_and_takes_no_step_at_the_eat(host):
    rows = floor_run(host, one_food("Base.Apple", False), 1)
    i = MEALS_3[1]                                                     # the second portion, 5 h after the first
    assert rows[i][3] == pytest.approx(4.3 * 2 ** (-5 / 72.0))
    assert rows[i][1] == pytest.approx(22 / 60)                       # one minute of the rise, not the 4.3
    assert rows[i][2] == pytest.approx(25 / 60)                       # BOREDOM: one BORED level a game hour
    assert rows[i + 15][3] <= rows[i + 15][1] < rows[i + 15][3] + host.K.hybrid.FLOOR_EPS   # met, a held fall over


RELEASE_DAYS = 26                                       # 14 days of one food, then 12 of variety: past n = 1


@pytest.fixture(scope="module")
def release(host):
    def plan(day, minute):
        if minute not in MEALS_3:
            return None
        if day < 14:
            return ("Base.Apple", False)
        return ("Base.Var%d_%d" % (day, minute), False)               # every portion a new type
    rows = floor_run(host, plan, RELEASE_DAYS)
    last_apple = AGE + (13 * 1440 + MEALS_3[2]) / 60.0
    seq = [AGE + (d * 1440 + mm) / 60.0 for d in range(14) for mm in MEALS_3]
    n0 = sum(2 ** (-(last_apple - a) / 72.0) for a in seq)
    return rows, last_apple, n0


def EPS(host):
    return host.K.hybrid.FLOOR_EPS


def test_a_varied_diet_releases_the_floor_as_the_counts_decay(host, release):
    rows, last_apple, n0 = release
    eps = EPS(host)
    # the count n0 after the last apple, then n0 x 2^(-t/72): the level leaves the cap when 4.3 (n - 1) < 30 and
    # reaches 0 when n reaches one portion, the window edge at 168 h passing with no step
    for r in rows[14 * 1440:]:
        dt = r[0] - last_apple
        want = min(30.0, 4.3 * max(0.0, n0 * 2 ** (-dt / 72.0) - 1))
        assert r[3] == pytest.approx(want, abs=1e-9)
        assert want - 1e-9 <= r[1] < want + eps and want - 1e-9 <= r[2] < want + eps      # held under one epsilon
    leave = 72 * math.log2(n0 * 4.3 / 34.3)
    assert 2 * 24 < leave < 2.5 * 24                                   # about 2.2 days at the cap
    zero = 72 * math.log2(n0)
    assert 11 * 24 < zero < 11.5 * 24                                  # n reaches one portion about 11.2 days on
    assert rows[-1][1] == pytest.approx(0, abs=1e-12) and rows[-1][2] == pytest.approx(0, abs=1e-12)   # landed


def test_the_release_takes_no_step_at_the_window_edge(host, release):
    # Plan 11f Task 9b fix 1: no single minute drops the target by more than the decay's own steepest per-minute
    # fall (at the cap's exit, 4.3 x n x ln 2 / 72 / 60 with n = 30 / 4.3 + 1), nor the stat by more than that plus
    # the write epsilon; before the fix the window edge dropped about 7 in one minute
    rows, last_apple, n0 = release
    eps = EPS(host)
    steep = 4.3 * (30 / 4.3 + 1) * math.log(2) / 72 / 60
    drops_t = [rows[i - 1][3] - rows[i][3] for i in range(14 * 1440 + 1, len(rows))]
    drops_u = [rows[i - 1][1] - rows[i][1] for i in range(14 * 1440 + 1, len(rows))]
    drops_b = [rows[i - 1][2] - rows[i][2] for i in range(14 * 1440 + 1, len(rows))]
    assert max(drops_t) <= steep * (1 + 1e-9)
    assert max(drops_u) < eps + steep and max(drops_b) < eps + steep
    edge = next(i for i, r in enumerate(rows) if r[0] - last_apple > 168)
    assert rows[edge][3] > 6.9 and rows[edge - 1][3] - rows[edge][3] < steep  # the edge: still about 7.0, no step


def test_a_decaying_target_sets_the_stat_at_most_once_per_epsilon_of_fall(host, release):
    # Rule 6: the floor holds a fall under FLOOR_EPS and folds it into the next write, so a decaying target writes
    # each stat about once per FLOOR_EPS of fall, not every minute; the fall to 0 lands whatever its size
    rows, last_apple, n0 = release
    eps = EPS(host)
    tail = rows[14 * 1440 + 60:]                                      # past the last apple's rise
    for col in (1, 2):
        sets = [(rows_i, a, b) for rows_i, (a, b) in enumerate(zip(tail, tail[1:])) if b[col] != a[col]]
        assert sets
        for _, a, b in sets:
            assert a[col] - b[col] >= eps - 1e-12 or b[3] == 0
        assert len(sets) <= 30 / eps + 1
        minutes = sum(1 for a, b in zip(tail, tail[1:]) if b[3] < a[3])
        assert len(sets) * 5 < minutes                                  # far fewer writes than falling minutes


def test_a_staple_only_diet_sits_at_a_quarter(host, mono14):
    rows = floor_run(host, one_food("Base.Bread", True), 14)
    assert max(r[1] for r in rows) == pytest.approx(7.5)
    assert rows[-1][1] == pytest.approx(0.25 * mono14[-1][1])


def test_one_portion_a_day_holds_under_the_cap(host):
    def plan(day, minute):
        return ("Base.Apple", False) if minute == 13 * 60 else None
    rows = floor_run(host, plan, 14)
    steady = 4.3 * (1 / (1 - 2 ** (-24 / 72.0)) - 1)                 # 16.54, the limit after an eat
    day13 = 4.3 * (sum(2 ** (-24 * j / 72.0) for j in range(14)) - 1)
    assert max(r[1] for r in rows) < steady < 30
    assert max(r[3] for r in rows[13 * 1440:]) == pytest.approx(day13, rel=1e-9)
    assert max(r[1] for r in rows[13 * 1440:]) == pytest.approx(day13, rel=5e-3)    # met a few minutes after the eat


def test_an_unhealed_non_table_entry_reads_level_zero_and_does_not_raise(host):
    m = host.rt.eval("{ t = { ['Base.A'] = 3, ['Base.B'] = 'x' } }")
    assert M(host).level(3, AGE) == 0
    assert tgt(host, m, AGE) == (0, 0)


# --- the mood floor's dead zone (Plan 15 Task 9; spec section 4, item 10c) ------------------------------------------

def test_the_dead_zone_constants_name_their_game_choice_and_thresholds(host):
    m = M(host)
    assert (m.DEAD_ZONE, m.HOLD_EPS) == (0.02, 0.01)
    assert [m.UNHAPPY_AT[i] for i in (1, 2)] == [20, 45] and [m.BORED_AT[1]] == [25]
    with open(KERNEL, encoding="utf-8") as fh:
        src = fh.read()
    for name in ("DEAD_ZONE", "HOLD_EPS"):
        line = dial_line("monotony." + name)
        assert "game choice (spec section 10: the dead-zone width" in line, name
    for name in ("UNHAPPY_AT", "BORED_AT"):
        assert "#2369" in re.search(r"^K\.monotony\.%s = .*$" % name, src, re.M).group(0), name


@pytest.mark.parametrize("v,prev,want", [
    (19.8, 20.5, 20.01),     # fallen under UNHAPPY 20 by 0.2, inside 0.02 x 20 = 0.4: held just over it
    (20.0, 25.0, 20.01),     # onto the threshold (the moodle is strict >): held
    (19.61, 20.5, 20.01),
    (19.6, 20.5, 19.6),      # at the zone's edge: released
    (19.0, 20.5, 19.0),      # past the zone: the fall stands
    (19.8, 20.005, 20.005),  # never held above the last target
    (44.5, 46.0, 45.01),     # the level-2 step (zone 0.9)
    (21.0, 19.0, 21.0),      # a rise is never held
    (19.8, 19.9, 19.8),      # the last target was not over the threshold
    (10.0, 30.0, 10.0),
])
def test_a_fall_inside_the_dead_zone_holds_over_the_threshold(host, v, prev, want):
    assert M(host).hold(v, prev, M(host).UNHAPPY_AT) == pytest.approx(want)


def test_the_boredom_threshold_and_junk(host):
    m = M(host)
    assert m.hold(24.6, 26.0, m.BORED_AT) == pytest.approx(25.01) and m.hold(24.5, 26.0, m.BORED_AT) == 24.5
    for v, prev in ((float("nan"), 21.0), (19.8, float("nan")), (19.8, None), (None, 21.0)):
        got = m.hold(v, prev, m.UNHAPPY_AT)
        assert got == v or (got != got and v != v), (v, prev)   # v returned as it is


# --- Plan 19 Task 2: the dials are the registry's (ruling T1-1) -----------------------------------------------------

MONOTONY_DIALS = ("WINDOW_H", "HALF_LIFE_H", "SLOPE", "CAP", "STAPLE", "MEAL_KCAL", "BORED_MAX", "DEAD_ZONE", "HOLD_EPS")


def test_each_dial_line_reads_its_registry_row_and_the_thresholds_stay_vanilla():
    with open(KERNEL, encoding="utf-8") as fh:
        src = fh.read()
    for name in MONOTONY_DIALS:
        assert re.search(r'^K\.monotony\.%s = K\.dials\.get\("monotony\.%s"\)$' % (name, name), src, re.M), name
    for name in ("UNHAPPY_AT", "BORED_AT"):                             # vanilla mirrors (#2369) stay in the kernel
        assert re.search(r"^K\.monotony\.%s = \{ [0-9, ]+ \} -- VANILLA #2369" % name, src, re.M), name


def test_each_field_holds_its_registry_value(host):
    rows = host.G.NutritionRevamp.data.dials
    for name in MONOTONY_DIALS:
        assert M(host)[name] == rows["monotony." + name].value, name


def test_a_registry_value_reaches_the_floor_at_load():
    # the mutation probe (dial-inventory section 3.4): the registry's SLOPE, edited before the kernels load, sets the
    # level, so the kernel holds no copy of its own
    import lupa.lua51 as lua51
    from .conftest import CORE, DIALS, kernel_files
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    load = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    for path in [CORE, DIALS] + kernel_files():
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        if path == DIALS:
            assert src.count("D['monotony.SLOPE'] = { value = 4.3,") == 1
            src = src.replace("D['monotony.SLOPE'] = { value = 4.3,", "D['monotony.SLOPE'] = { value = 5.0,")
        load(src, "@" + os.path.basename(path))()
    k = rt.globals().NutritionRevamp.kernel
    m = k.monotony.new()
    for d in range(3):
        k.monotony.record(m, "Base.Apple", AGE + d * DAY, 1, False)
    u, b = k.monotony.target(m, AGE + 2 * DAY)
    assert k.monotony.SLOPE == 5.0
    assert u == pytest.approx(5.0 * (decay(2 * DAY) + decay(DAY))) and b == u
