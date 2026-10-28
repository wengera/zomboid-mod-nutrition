"""`agent.base.items` (Plan 23 Task 9, P23-D): an item's use read off `data/food-items.json` (food by `kind == "food"`,
water by `kind == "fluid_container"`), a bandage by the Lua loot's own name rule, a weapon by `WEAPON_RX`, else other.
Every expectation is checked against the dataset read here, never a literal count or a remembered membership.
"""
import json
import os

from agent.base import items

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _dataset():
    with open(os.path.join(ROOT, "data", "food-items.json"), encoding="utf-8") as f:
        return {it["id"]: it for it in json.load(f)["items"]}


DATA = _dataset()


def test_the_index_is_the_datasets_food_and_fluid_containers():
    assert items.FOOD_IDS == frozenset(i for i, it in DATA.items() if it["kind"] == "food")
    assert items.DRINK_IDS == frozenset(i for i, it in DATA.items() if it["kind"] == "fluid_container")
    assert items.FOOD_IDS and items.DRINK_IDS and not items.FOOD_IDS & items.DRINK_IDS


def test_carrots_are_food():
    assert DATA["Base.Carrots"]["kind"] == "food"
    assert items.use_of("Base.Carrots") == "food"


def test_the_plan_22_misses_are_food_where_the_dataset_has_them():
    """The four names the survival runs' held-food regex missed: each the dataset carries is food; a name it does not
    carry (on 42.21, `Base.PowerBar`) reads `other` and is reported, never forced."""
    names = ("Base.CannedMilk", "Base.TinnedSoup", "Base.Macandcheese", "Base.PowerBar")
    present = [n for n in names if n in DATA]
    assert len(present) >= 3, present
    for n in present:
        assert DATA[n]["kind"] == "food", n
        assert items.use_of(n) == "food", n
    for n in set(names) - set(present):
        assert items.use_of(n) == "other", n


def test_a_hammer_is_not_food_and_is_a_weapon_by_the_rx():
    assert "Base.Hammer" not in items.FOOD_IDS
    assert items.use_of("Base.Hammer") != "food"
    assert items.use_of("Base.Hammer") == "weapon"


def test_a_fluid_container_is_water_whatever_its_name():
    fc = sorted(i for i, it in DATA.items() if it["kind"] == "fluid_container")
    for i in fc:
        assert items.use_of(i) == "water", i
    if "Base.Bowl" in DATA:                                       # the bowl Plan 22's WATER_RX matched by name
        want = "water" if DATA["Base.Bowl"]["kind"] == "fluid_container" else "other"
        assert items.use_of("Base.Bowl") == want


def test_a_drainable_is_not_food_or_water():
    dr = sorted(i for i, it in DATA.items() if it["kind"] == "drainable")
    assert dr
    for i in dr:
        assert items.use_of(i) not in ("food", "water"), i


def test_bandages_by_the_lua_loots_name_rule_and_the_rest_other():
    assert items.use_of("Base.Bandage") == "bandage"
    assert items.use_of("Base.RippedSheets") == "other"           # the Lua rule is Bandage or Rag in the name
    assert items.use_of("Base.Rag") == "bandage"
    assert items.use_of("Base.Nails") == "other"
    assert items.use_of(None) == "other" and items.use_of("") == "other"


def test_the_uses_are_the_five_names():
    assert items.USES == ("food", "water", "weapon", "bandage", "other")
