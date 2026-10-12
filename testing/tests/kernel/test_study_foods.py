"""TKX_StudyFoods (Plan 11f Task 2): the experiment mod's foods declare the satiety oracles' meal vectors.

Each item's four macros are its script values (the live getters read their float32) and its water and fibre ride the
NR_Nutrients key, the mod's declared-nutrients seam (K.vector.declared, IN.declaredOf; landing #3148). This pins, for
every food: the script's vector against the oracle vector it names (test_satiety_meal_studies.py's mixed, snack,
CASSEROLE, SOUP, MARC_SOLID, MARC_SOUP, dense and the water-only meals), at float32 precision; boredom, unhappiness and
stress changes 0; the staple's FoodType Bread and the non-staple's not; and that an eat of each, through the mod's own
intake adapter (IN.readAfterAndLand on a before-snapshot, tools/replay_live.py's ServerReplay), lands source declared
with the oracle vector in the stomach and the pool fed by its weighed kcal. The layout passes mod_lint and the release
check with no ERROR. Nothing here is a kernel file, so the coverage gate is untouched.
"""
import os
import sys

import pytest

from . import test_satiety_meal_studies as M
from .server_host import REPO

sys.path.insert(0, os.path.join(REPO, "tools"))
import replay_live as RL  # noqa: E402
import mod_lint  # noqa: E402
import release_pack  # noqa: E402

MOD = os.path.join(REPO, "testing", "experiments", "TKX_StudyFoods")
REL = 1e-6                       # float32 of a script value, and the script's six decimals


def oracle_vectors():
    """The vector each study food must land, from the oracle's own constructors."""
    out = {
        "TKX.Mixed650": M.mixed(650),
        "TKX.Mixed400": M.mixed(400, water=250.0),
        "TKX.Mixed217": M.mixed(650 / 3, water=100.0, fibre=2.0),
        "TKX.Mixed667": M.mixed(2000.0 / 3, water=900.0 / 3, fibre=6.0 * (2000.0 / 3) / 650),
        "TKX.Mixed333": M.mixed(2000.0 / 6, water=900.0 / 6, fibre=6.0 * (2000.0 / 6) / 650),
        "TKX.SnackP": M.snack(239.0, "proteins", 0.77),
        "TKX.SnackC": M.snack(239.0, "carbs", 0.84),
        "TKX.SnackF": M.snack(239.0, "lipids", 0.58),
        "TKX.Casserole": M.CASSEROLE,
        "TKX.Soup": M.SOUP,
        "TKX.Marc": M.MARC_SOLID,
        "TKX.MarcSoup": M.MARC_SOUP,
        "TKX.Dense400Lo": M.dense(400.0, 0.8),
        "TKX.Dense400Hi": M.dense(400.0, 1.6),
        "TKX.Mono450": M.mixed(450.0, water=300.0 * 450 / 650, fibre=6.0 * 450 / 650),
        "TKX.Staple450": M.mixed(450.0, water=300.0 * 450 / 650, fibre=6.0 * 450 / 650),
        "TKX.Unit50": M.mixed(50.0, water=300.0 * 50 / 650, fibre=6.0 * 50 / 650),
        "TKX.MilkSolid": MILK_SOLID,
    }
    for g in (100, 200, 300, 400, 500, 600):
        out["TKX.Water%d" % g] = {"water": float(g)}
    return out


KEYS = ("calories", "carbs", "lipids", "proteins", "water", "fibre")
# Plan 11f Task 4 (research row 4): the declared solid twin of 0.5 L of the vanilla fluid CowMilk, the mod's per-litre
# fluid-table entry (NR_Data_Nutrients.lua FLUIDS.CowMilk) times 0.5 on the macros and the water
MILK_L = 0.5
MILK_SOLID = {"calories": 314.15, "carbs": 24.72, "lipids": 16.7375, "proteins": 16.2225, "water": 453.8695}


def close(a, b):
    return abs(a - b) <= REL * max(1.0, abs(b))


def test_every_study_food_is_declared_and_no_other():
    assert set(RL.study_foods()) == set(oracle_vectors())


def test_each_scripts_vector_is_its_oracles():
    foods = RL.study_foods()
    for full, want in oracle_vectors().items():
        got = RL.declared_vector(foods[full])
        for k in KEYS:
            assert close(got.get(k, 0.0), want.get(k, 0.0)), (full, k, got.get(k), want.get(k))


def test_the_snacks_carry_the_oracles_shares_and_239_kcal():
    foods = RL.study_foods()
    for name, key, atw, share in (("TKX.SnackP", "pro", 4, 0.77), ("TKX.SnackC", "carb", 4, 0.84),
                                  ("TKX.SnackF", "lip", 9, 0.58)):
        s = foods[name]
        assert s["cal"] == 239.0
        assert close(s[key] * atw / 239.0, share), name


def test_every_food_has_no_mood_or_thirst_change_and_a_hunger_change():
    for full, s in RL.study_foods().items():
        assert s["boredom"] == 0 and s["unhappy"] == 0 and s["stress"] == 0 and s["thirst"] == 0, full
        assert s["hunger"] < 0, full                 # a share is read off the hunger drop (K.intake.fractionOf)
        assert s["declared"], full


def test_the_staple_is_bread_and_the_rest_are_not_staples():
    foods = RL.study_foods()
    assert foods["TKX.Staple450"]["foodType"] == "Bread"
    staples = {"Bread", "Rice", "Pasta"}
    assert [f for f, s in foods.items() if s["foodType"] in staples] == ["TKX.Staple450"]
    assert foods["TKX.Mono450"]["foodType"] == "NoExplicit"


def test_the_unit_is_50_kcal_of_the_650_meals_composition():
    foods = RL.study_foods()
    u, m = RL.declared_vector(foods["TKX.Unit50"]), RL.declared_vector(foods["TKX.Mixed650"])
    assert u["calories"] == 50.0
    for k in KEYS:
        assert close(u[k] * 13, m[k]), k


def test_the_layout_passes_the_lint_and_the_release_check_with_no_error():
    assert not [f for f in mod_lint.lint([MOD]) if f.level == mod_lint.ERROR]
    assert not [f for f in release_pack.check(MOD) if f.level == release_pack.ERROR]
    with open(os.path.join(MOD, "42.20.4", "mod.info"), encoding="utf-8") as fh:
        info = fh.read()
    assert "id=TKX_StudyFoods" in info and "versionMin=42.20.4" in info


@pytest.mark.parametrize("full", sorted(oracle_vectors()))
def test_an_eat_lands_the_oracle_vector_through_the_declared_chain(full):
    want = oracle_vectors()[full]
    rp = RL.ServerReplay(start={"username": "admin", "firstSeen": 99.0, "lastSeen": 99.0,
                                "satiety": {"M": 10.0, "S": 0, "L": 0, "t": 99.0}}, user="admin")
    rp.apply({"kind": "eat", "food": full}, 100.0)
    rec = rp.record()
    v = rp.K.vector.new()
    for k, x in want.items():
        v[k] = x
    assert rec.satiety.M == pytest.approx(10.0 + rp.K.satiety.weigh(v), rel=REL)   # Plan 11g Task 6c: M fed at the eat
    assert rp.K.satiety.weigh(rec.stomach.buffer) == pytest.approx(rp.K.satiety.weigh(v), rel=REL)
    assert rec.lastIntake.source == "declared" and rec.lastIntake.share == 1 and rec.lastIntake.frac == 1
    assert list(rec.lastIntake.declared.values()) == [full]
    buf = rec.stomach.buffer
    for k in KEYS:
        assert close(buf[k], want.get(k, 0.0)), (full, k, buf[k], want.get(k, 0.0))
    for k in ("vitC", "iron", "sodium", "ethanol", "caffeine"):
        assert buf[k] == 0, (full, k)
    assert rp.eats[0]["kcal"] == pytest.approx(want.get("calories", 0.0), rel=REL)


def test_the_milk_solid_is_half_a_litre_of_the_fluid_tables_cow_milk():
    rp = RL.ServerReplay(user="admin")
    milk = rp.NR.data.fluids.get("CowMilk")
    for k, v in MILK_SOLID.items():
        assert close(v, milk[k] * MILK_L), (k, v, milk[k])


def test_every_int_typed_key_parses_as_the_engine_int():
    """Item.DoParam reads BoredomChange, UnhappyChange, StressChange, DaysFresh and DaysTotallyRotten with
    Integer.parseInt (#0214, the key table in docs/facts/food-item-model.md), and a malformed value throws
    InvalidParameterException and drops the item (#0213); a debug client then dies on the script load. x260's first
    boot (2026-10-10) lost all 23 foods to `0.0` on the three mood keys."""
    import re
    rx = re.compile(r"^[+-]?\d+$")
    path = os.path.join(MOD, "common", "media", "scripts", "tkx_study_foods.txt")
    with open(path, encoding="utf-8") as fh:
        lines = [ln.strip().rstrip(",") for ln in fh]
    keys = ("BoredomChange", "UnhappyChange", "StressChange", "DaysFresh", "DaysTotallyRotten")
    seen = 0
    for ln in lines:
        k, _, v = ln.partition("=")
        if k.strip() in keys:
            seen += 1
            assert rx.match(v.strip()), ln
    assert seen == 24 * len(keys)
