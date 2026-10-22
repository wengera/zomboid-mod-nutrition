"""tools/hedonics_budget.py (Plan 19 Task 5; spec section B.3): the food hedonics budget oracle. Six reference diets over
14 days on the replay host, the mod's food mood against vanilla's model of the same eats, its bands as dials
(hedonics.BUDGET_FAIR, hedonics.BUDGET_DEGEN). The diets keep the character alive and hydrated (rule R-1, through the
mod's server pipeline); every band passes at the registry's dials and at each hedonics dial x0.8 and x1.2 (no cliff);
the bands' direction is pinned (a mutation inverting one fails here)."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import hedonics_budget as HB  # noqa: E402


@pytest.fixture(scope="module")
def oracle():
    return HB.Oracle()


@pytest.fixture(scope="module")
def rows(oracle):
    return oracle.rows()


def by(rows):
    return {label: r for label, _, r in rows}


def test_every_band_passes_at_the_registry(oracle, rows):
    ver = oracle.verdicts(rows)
    assert all(ok for _, ok, _ in ver), [v for v in ver if not v[1]]
    kinds = {label: kind for label, kind, _ in rows}
    assert kinds["mixed"] == "balanced" and kinds["canned"] == "reported"
    assert [kinds[d] for d in ("butter", "sugar", "one food")] == ["degenerate"] * 3
    assert [kinds["cooked (Cooking %d)" % lv] for lv in HB.COOKING_LEVELS] == ["cooked"] * 3
    fair, degen = oracle.bands()
    assert (fair, degen) == (float(oracle.K.hedonics.BUDGET_FAIR), float(oracle.K.hedonics.BUDGET_DEGEN))


def test_the_diets_are_meals_a_survivor_lives_on(oracle, rows):
    for diet in HB.DIETS:
        _, v = oracle.body(diet)                          # rule R-1 already asserted: alive, no drain, under the bound
        assert v["death"] is None and v["drain"] is None, diet
    for label, _, r in rows:
        assert 2200 <= r["kcal_day"] <= 3500, label


def test_the_bands_direction(oracle):
    # mutation: a band inverted (a degenerate diet passing when it is not sadder, a fair one when it is) fails here
    fair, degen = 5.0, 15.0
    def row(kind, du, db=0.0):
        return [("x", kind, {"du": du, "db": db})]
    def ok(kind, du, db=0.0):
        return oracle.verdicts(row(kind, du, db), fair, degen)[0][1]
    assert ok("degenerate", 15.0) and not ok("degenerate", 14.99) and not ok("degenerate", -30)
    assert ok("balanced", 5.0) and not ok("balanced", 5.01) and not ok("balanced", 0, 5.01)
    assert ok("cooked", -40) and not ok("cooked", 6)
    assert ok("reported", 99, 99)


def test_rule_r1_reaches_the_sugar_diet_and_spares_the_mixed_one(rows):
    r = by(rows)
    assert r["sugar"]["floor"] > 0
    assert r["mixed"]["floor"] == 0                       # an occasional butter is vanilla's own sadness
    assert r["butter"]["floor"] == 0                      # salted butter is a fat and sodium pairing (S2291; the report's concern)


def test_the_floor_ceiling_and_the_writer_cap(oracle, rows):
    r = by(rows)
    hi = float(oracle.K.dials.get("writer.UNHAPPY_HI"))
    assert r["sugar"]["floor"] == pytest.approx(float(oracle.K.hedonics.FLOOR_KNOTS[3][2]))
    assert r["sugar"]["target"] == pytest.approx(hi)
    assert all(x["target"] <= hi + 1e-9 for x in r.values())


def test_the_hedonics_add_nothing_to_the_balanced_and_cooked_diets(oracle, rows):
    # the balanced and cooked diets' excess is the existing monotony's: with every hedonics rule neutral the rows read
    # the same (R1's floor 0, R3's scale 1, R4's weight 0, R2's scale 1 at every level)
    K = oracle.K
    saved = (K.hedonics.CLASS_W, K.hedonics.ALLIES_F, K.hedonics.PREP_KNOTS[1][2], K.hedonics.PREP_KNOTS[3][2])
    try:
        K.hedonics.CLASS_W = 0
        K.hedonics.ALLIES_F = 1
        K.hedonics.PREP_KNOTS[1][2] = 1
        K.hedonics.PREP_KNOTS[3][2] = 1
        off = by(oracle.rows())
    finally:
        K.hedonics.CLASS_W, K.hedonics.ALLIES_F, K.hedonics.PREP_KNOTS[1][2], K.hedonics.PREP_KNOTS[3][2] = saved
    r = by(rows)
    for label in ["mixed"] + ["cooked (Cooking %d)" % lv for lv in HB.COOKING_LEVELS]:
        assert abs(r[label]["du"] - off[label]["du"]) < 0.05, label
        assert off[label]["du"] > 0                       # the monotony the mod already had


def test_the_mood_model_by_hand(oracle):
    # one sad eat of +20 at minute 0, eaten Hungry, then 120 minutes of upkeep at 1 a game hour
    K = oracle.K
    f = float(K.hedonics.ALLIES_F)
    eat = {"minute": 0, "key": "Base.Lard", "kcal": 100.0, "unhappy": 20.0, "bored": 0.0, "plain": True,
           "class": "fatty", "staple": False, "dish": False, "hunger": 0.5}
    lua = oracle.rt.table_from([oracle.rt.table_from(eat)])
    vu, vb, mu, mb, fl, tg = oracle.rt.globals().NR_BUDGET.run(lua, 1, 120, 1.0, 0.0, 59.0)
    want = sum(20.0 - (t + 1) / 60.0 for t in range(120)) / 120
    assert vu == pytest.approx(want) and vb == 0
    assert mu == pytest.approx(sum(20.0 * f - (t + 1) / 60.0 for t in range(120)) / 120)
    assert fl == 0 and tg == 0                            # 100 kcal is under the share's minimum intake: no floor


def test_no_cliff_under_the_sweep(oracle):
    sweep = oracle.sweep()
    assert set(sweep) == set(HB.SWEEP)
    moved = set()
    base = by(oracle.rows())
    for dial, arms in sweep.items():
        for name, r2 in arms.items():
            ver = oracle.verdicts(r2)
            assert all(ok for _, ok, _ in ver), (dial, name, [v for v in ver if not v[1]])
            for label, _, r in r2:
                if abs(r["du"] - base[label]["du"]) > 0.01 or abs(r["db"] - base[label]["db"]) > 0.01:
                    moved.add(dial)
    # the dials the reference diets read (the rest are flat by construction, each named in the Task 5 report)
    for dial in ("hedonics.SHARE_MIN_KCAL", "hedonics.FLOOR_KNOTS.3.1", "hedonics.FLOOR_KNOTS.3.2", "hedonics.CLASS_W"):
        assert dial in moved, dial
    assert oracle.K.hedonics.CLASS_W == float(oracle.K.dials.get("hedonics.CLASS_W"))   # every dial restored


def test_the_tool_runs_and_names_its_bands(oracle, capsys):
    assert HB.main([], oracle) == 0
    out = capsys.readouterr().out
    assert "bands FAIR" in out and "DEGEN" in out and "FAIL" not in out
