"""`agent.base.items` (Plan 23 Task 9, P23-D): an item's use read off `data/food-items.json` (food by `kind == "food"`,
water by a drinkable `fluid_container` whose fluids are not all poisons), a bandage by the Lua loot's own name rule, a
weapon by `WEAPON_RX`, else other. Every expectation is checked against the dataset read here, never a literal count
or a remembered membership.
"""
import json
import os

from agent.base import items

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _dataset():
    with open(os.path.join(ROOT, "data", "food-items.json"), encoding="utf-8") as f:
        d = json.load(f)
    return {it["id"]: it for it in d["items"]}, {fl["id"]: fl for fl in d["fluids"]}


DATA, FLUIDS = _dataset()
POISONS = frozenset(i for i, fl in FLUIDS.items() if fl.get("poison"))


def _poison_only(it):
    return bool(it.get("fluid_ids")) and set(it["fluid_ids"]) <= POISONS


def _water(it):
    """The dataset's own columns: a drinkable fluid container whose named fluids are not all poisons."""
    return it["kind"] == "fluid_container" and bool(it.get("drinkable")) and not _poison_only(it)


def test_the_index_is_the_datasets_food_and_fluid_containers():
    assert items.FOOD_IDS == frozenset(i for i, it in DATA.items() if it["kind"] == "food")
    assert items.DRINK_IDS == frozenset(i for i, it in DATA.items() if _water(it))
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


def test_a_drinkable_fluid_container_is_water_whatever_its_name():
    fc = sorted(i for i, it in DATA.items() if _water(it))
    assert fc
    for i in fc:
        assert items.use_of(i) == "water", i
    assert DATA["Base.WaterBottle"]["drinkable"] and items.use_of("Base.WaterBottle") == "water"


def test_a_non_drinkable_fluid_container_is_not_water():
    """Petrol cans, buckets, sprayers: the dataset marks them `drinkable` false, so they fall to the name rules."""
    dry = sorted(i for i, it in DATA.items() if it["kind"] == "fluid_container" and not it.get("drinkable"))
    assert dry
    for i in dry:
        assert items.use_of(i) != "water", i
    petrol = [i for i in dry if "Petrol" in (DATA[i].get("fluid_ids") or ())]
    assert petrol                                                 # PetrolCan, JerryCan on 42.21
    for i in petrol:
        assert items.use_of(i) == "other", i


def test_a_drinkable_container_of_only_poisons_is_not_water():
    """Bleach, hair dye: drinkable containers in the dataset whose every fluid carries `poison` in `fluids`."""
    poison = sorted(i for i, it in DATA.items()
                    if it["kind"] == "fluid_container" and it.get("drinkable") and _poison_only(it))
    assert "Base.Bleach" in poison and any("HairDye" in i for i in poison), poison
    for i in poison:
        assert items.use_of(i) != "water", i


def test_an_empty_named_container_reads_as_the_dataset_says():
    """A deliberate change from Plan 22's regex (which never read `...Empty` as water): an `Empty`-named container
    reads water when the dataset calls it a drinkable, non-poison fluid container, else not; its fill is the Lua's and
    `World.mark_empty`'s to judge."""
    empties = sorted(i for i, it in DATA.items() if it["kind"] == "fluid_container" and i.endswith("Empty"))
    assert any(_water(DATA[i]) for i in empties) and any(not _water(DATA[i]) for i in empties), empties
    for i in empties:
        assert (items.use_of(i) == "water") == _water(DATA[i]), i


def test_a_drainable_is_not_food_or_water():
    dr = sorted(i for i, it in DATA.items() if it["kind"] == "drainable")
    assert dr
    for i in dr:
        assert items.use_of(i) not in ("food", "water"), i


def test_bandages_by_the_lua_loots_name_rule_and_the_rest_other():
    assert items.use_of("Base.Bandage") == "bandage"
    assert items.use_of("Base.RippedSheets") == "other"           # the Lua rule is Bandage or Rag in the name
    assert items.use_of("Base.Rag") == "bandage"
    if "Base.RagFilter" in DATA and not _water(DATA["Base.RagFilter"]):
        assert items.use_of("Base.RagFilter") == "bandage"        # the Lua's name rule reads it a bandage too
    assert items.use_of("Base.Nails") == "other"
    assert items.use_of(None) == "other" and items.use_of("") == "other"


def test_the_uses_are_the_five_names():
    assert items.USES == ("food", "water", "weapon", "bandage", "other")
