"""Monotony at the eat (Plan 11e Task 3, ruling 11e-1): K.monotony on the kernel host.

A per-player record of recent eats by full type, record.monotony = { t = { [fullType] = { n, last } } }: n is the
decayed count of eats (item-equivalents, a partial eat counting its share) at world age `last`, decaying with a
3-day half-life; an entry whose last eat is beyond the 7-day window counts 0 and is pruned. The delta an eat
delivers to BOREDOM and to UNHAPPINESS is share x min(CAP, slope x max(0, n - 1)), n the decayed count including
this eat, the slope reduced to STAPLE x SLOPE for a staple. Hand-computed from the constants.
"""
import math
import os
import re

import pytest

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
    assert (m.WINDOW_H, m.HALF_LIFE_H, m.SLOPE, m.CAP, m.STAPLE) == (168, 72, 4.3, 20, 0.25)


def test_each_constant_names_its_rows_and_its_label():
    with open(KERNEL, encoding="utf-8") as fh:
        src = fh.read()
    for name in ("WINDOW_H", "HALF_LIFE_H", "SLOPE", "CAP", "STAPLE"):
        line = re.search(r"^K\.monotony\.%s = .*$" % name, src, re.M).group(0)
        assert "game choice, Plan 11e (ruling 11e-1)" in line, name
    assert "#0042" in re.search(r"^K\.monotony\.SLOPE = .*$", src, re.M).group(0)
    assert "#0042" in re.search(r"^K\.monotony\.CAP = .*$", src, re.M).group(0)
    for row in ("S1592", "S1593", "S1594", "S1595", "S1596", "S1597"):
        assert row in src, row
    assert "free choice" in src                                         # S1594: the player choosing variety


def test_new_is_an_empty_type_map(host):
    m = M(host).new()
    assert host.py(m) == {"t": {}}


# --- the delta's shape ---------------------------------------------------------------------------------------


def test_the_first_eat_of_a_type_gives_nothing(host):
    m = M(host).new()
    assert M(host).delta(m, "Base.Apple", AGE, False, 1) == (0, 0)


def test_repeats_grow_by_the_slope_per_recent_eat(host):
    m = M(host).new()
    got = []
    for i in range(4):
        got.append(M(host).delta(m, "Base.Apple", AGE, False, 1)[0])
        M(host).record(m, "Base.Apple", AGE, 1)
    assert got == pytest.approx([0, 4.3, 8.6, 12.9])


def test_both_stats_take_the_same_delta(host):
    m = M(host).new()
    M(host).record(m, "Base.Apple", AGE, 1)
    b, u = M(host).delta(m, "Base.Apple", AGE, False, 1)
    assert b == u == pytest.approx(4.3)


def test_the_fifth_daily_eat_reads_about_a_stale_item(host):
    # the anchor: one eat a day, the fifth reads 4.3 x (2^-1/3 + 2^-2/3 + 2^-1 + 2^-4/3) = 9.978, vanilla's stale +10
    m = M(host).new()
    for d in range(4):
        M(host).record(m, "Base.Apple", AGE + d * DAY, 1)
    b, _ = M(host).delta(m, "Base.Apple", AGE + 4 * DAY, False, 1)
    want = 4.3 * sum(decay(k * DAY) for k in range(1, 5))
    assert b == pytest.approx(want, rel=1e-12)
    assert b == pytest.approx(9.978, abs=1e-3)


def test_the_delta_decays_after_days_uneaten(host):
    m = M(host).new()
    M(host).record(m, "Base.Apple", AGE, 1)
    M(host).record(m, "Base.Apple", AGE, 1)
    at0 = M(host).delta(m, "Base.Apple", AGE, False, 1)[0]
    at3 = M(host).delta(m, "Base.Apple", AGE + 3 * DAY, False, 1)[0]
    at6 = M(host).delta(m, "Base.Apple", AGE + 6 * DAY, False, 1)[0]
    assert at0 == pytest.approx(4.3 * 2)
    assert at3 == pytest.approx(4.3 * 2 * 0.5)                          # one half-life
    assert at6 == pytest.approx(4.3 * 2 * 0.25)


def test_beyond_the_window_a_type_counts_nothing(host):
    m = M(host).new()
    M(host).record(m, "Base.Apple", AGE, 1)
    M(host).record(m, "Base.Apple", AGE, 1)
    assert M(host).delta(m, "Base.Apple", AGE + 168, False, 1)[0] == pytest.approx(4.3 * 2 * decay(168))
    assert M(host).delta(m, "Base.Apple", AGE + 168.01, False, 1)[0] == 0


def test_staples_take_the_reduced_slope(host):
    m = M(host).new()
    M(host).record(m, "Base.Bread", AGE, 1)
    M(host).record(m, "Base.Bread", AGE, 1)
    assert M(host).delta(m, "Base.Bread", AGE, True, 1)[0] == pytest.approx(4.3 * 0.25 * 2)
    assert M(host).delta(m, "Base.Bread", AGE, False, 1)[0] == pytest.approx(4.3 * 2)


def test_the_cap_holds(host):
    m = M(host).new()
    for _ in range(10):
        M(host).record(m, "Base.Apple", AGE, 1)
    assert M(host).delta(m, "Base.Apple", AGE, False, 1)[0] == 20
    assert M(host).delta(m, "Base.Apple", AGE, False, 0.5)[0] == pytest.approx(10)   # the cap, then the share


def test_types_are_counted_apart(host):
    m = M(host).new()
    M(host).record(m, "Base.Apple", AGE, 1)
    M(host).record(m, "Base.Apple", AGE, 1)
    assert M(host).delta(m, "Base.Orange", AGE, False, 1)[0] == 0


def test_a_partial_eat_counts_its_share_and_scales_its_delta(host):
    m = M(host).new()
    M(host).record(m, "Base.Apple", AGE, 1)
    b, u = M(host).delta(m, "Base.Apple", AGE, False, 0.5)
    assert b == u == pytest.approx(0.5 * 4.3 * 0.5)                     # n = 1 + 0.5, x the share 0.5
    M(host).record(m, "Base.Apple", AGE, 0.5)
    assert m.t["Base.Apple"].n == pytest.approx(1.5)


def test_an_item_eaten_in_parts_is_not_monotonous_against_itself(host):
    m = M(host).new()
    for _ in range(4):
        assert M(host).delta(m, "Base.Apple", AGE, False, 0.25)[0] == 0
        M(host).record(m, "Base.Apple", AGE, 0.25)
    assert m.t["Base.Apple"].n == pytest.approx(1.0)


def test_a_nil_share_is_one_and_a_share_is_clamped(host):
    m = M(host).new()
    M(host).record(m, "Base.Apple", AGE)
    assert m.t["Base.Apple"].n == 1
    assert M(host).delta(m, "Base.Apple", AGE, False)[0] == pytest.approx(4.3)
    assert M(host).delta(m, "Base.Apple", AGE, False, 3)[0] == pytest.approx(4.3)
    assert M(host).delta(m, "Base.Apple", AGE, False, -1)[0] == 0


def test_record_decays_the_count_to_the_eat_and_stamps_it(host):
    m = M(host).new()
    M(host).record(m, "Base.Apple", AGE, 1)
    e = M(host).record(m, "Base.Apple", AGE + 72, 1)
    assert e.n == pytest.approx(1.5) and e.last == AGE + 72
    e = M(host).record(m, "Base.Apple", AGE + 72 + 169, 1)
    assert e.n == 1 and e.last == AGE + 72 + 169                         # past the window: a fresh count


def test_count_of_no_entry_is_zero(host):
    assert M(host).count(None, AGE) == 0


# --- pruning -------------------------------------------------------------------------------------------------


def test_prune_drops_only_the_types_beyond_the_window(host):
    m = M(host).new()
    M(host).record(m, "Base.Old", AGE - 169, 1)
    M(host).record(m, "Base.Older", AGE - 300, 1)
    M(host).record(m, "Base.Edge", AGE - 168, 1)
    M(host).record(m, "Base.New", AGE, 1)
    assert M(host).prune(m, AGE) == 2
    assert sorted(host.py(m.t)) == ["Base.Edge", "Base.New"]


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
                                     ("Base.Toast", None), ("Base.BagelPlain", None), ("Base.Tortilla", None)])
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
    M(host).record(m, "Base.Apple", AGE, 1)
    out, healed = M(host).heal(m, AGE)
    assert host.rt.eval("rawequal")(out, m) and healed is False


@pytest.mark.parametrize("raw", ["'junk'", "7", "{ t = 'x' }", "{ }", "{ t = { ['Base.A'] = 3 } }",
                                 "{ t = { [4] = { n = 1, last = 0 } } }",
                                 "{ t = { ['Base.A'] = { n = 0 / 0, last = 0 } } }",
                                 "{ t = { ['Base.A'] = { n = 1, last = 1 / 0 } } }",
                                 "{ t = { ['Base.A'] = { n = 'x', last = 0 } } }",
                                 "{ t = { ['Base.A'] = { n = -1, last = 0 } } }",
                                 "{ t = { ['Base.A'] = { n = 1, last = 2000 } } }",
                                 "{ t = { ['Base.A'] = { n = 1, last = 0 }, ['Base.B'] = { last = 0 } } }"])
def test_heal_resets_a_corrupt_table_and_says_so(host, raw):
    m, healed = M(host).heal(host.rt.eval(raw), AGE)
    assert host.py(m) == {"t": {}} and healed is True


def test_the_kernel_never_names_hunger():
    with open(KERNEL, encoding="utf-8") as fh:
        code = "\n".join(l.split("--")[0] for l in fh.read().splitlines())
    assert "HUNGER" not in code.upper().replace("HUNGER_", "")
