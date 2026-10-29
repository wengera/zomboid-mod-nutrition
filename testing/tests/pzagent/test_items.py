"""`agent.base.items` (Plan 23 Task 9, P23-D): an item's use read off `data/food-items.json` (food by `kind == "food"`,
water by a drinking vessel spawning holding only quenching fluids and unsealed, a container by one spawning empty:
PZA/1.4.1, 1.5, 1.5.1), a bandage by the scripts' CanBandage (PZA/1.5.1), a weapon by `WEAPON_RX`, else other. Every expectation is checked against the dataset read here, never a literal count
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


WATERS = ("Water", "CarbonatedWater")   # PZA/1.4.1 (P24-F): the jar's isWaterSource fluids less TaintedWater


def _quenches(fid):
    """PZA/1.5 (the Task 9 amendment): a dataset fluid in the Beverage category, neither Hazardous nor Alcoholic, with
    no poison block, whose thirst change is below 0."""
    fl = FLUIDS.get(fid) or {}
    cats = fl.get("categories") or ()
    t = fl.get("thirst_change")
    return ("Beverage" in cats and "Hazardous" not in cats and "Alcoholic" not in cats and not fl.get("poison")
            and isinstance(t, (int, float)) and t < 0)


def _vessel(it):
    """The dataset's own columns: a drinkable fluid container of at most 3 litres (vanilla's drink menu's cap)."""
    return (it["kind"] == "fluid_container" and bool(it.get("drinkable"))
            and (it.get("fluid_capacity") or 99.0) <= 3.0)


def _water(it):
    """A vessel spawning holding only fluids that quench (PZA/1.4.1's water, PZA/1.5's beverages), not sealed (PZA/1.5.1:
    a can tagged base:sealedbeveragecan spawns canPlayerEmpty false)."""
    return (_vessel(it) and bool(it.get("fluid_ids")) and all(f in WATERS or _quenches(f) for f in it["fluid_ids"])
            and "base:sealedbeveragecan" not in (it.get("tags") or ()))


def _container(it):
    """A vessel spawning empty (PZA/1.4.1)."""
    return _vessel(it) and not it.get("fluid_ids")


def test_the_index_is_the_datasets_food_and_fluid_containers():
    assert items.FOOD_IDS == frozenset(i for i, it in DATA.items()
                                       if it["kind"] == "food" and not it.get("cant_eat"))   # fix wave P, I-4
    assert items.DRINK_IDS == frozenset(i for i, it in DATA.items() if _water(it))
    assert items.FOOD_IDS and items.DRINK_IDS and not items.FOOD_IDS & items.DRINK_IDS


def test_carrots_are_food():
    assert DATA["Base.Carrots"]["kind"] == "food"
    assert items.use_of("Base.Carrots") == "food"


def test_the_plan_22_misses_are_food_where_the_dataset_has_them():
    """The four names the survival runs' held-food regex missed: each the dataset carries is food, unless it is a
    sealed can (`cant_eat`, fix wave P I-4: `TinnedSoup`, `Macandcheese` on 42.21), which reads `other`; a name it does
    not carry (on 42.21, `Base.PowerBar`) reads `other` and is reported, never forced."""
    names = ("Base.CannedMilk", "Base.TinnedSoup", "Base.Macandcheese", "Base.PowerBar")
    present = [n for n in names if n in DATA]
    assert len(present) >= 3, present
    for n in present:
        assert DATA[n]["kind"] == "food", n
        assert items.use_of(n) == ("other" if DATA[n].get("cant_eat") else "food"), n
    for n in set(names) - set(present):
        assert items.use_of(n) == "other", n


def test_a_hammer_is_not_food_and_is_a_weapon_by_the_rx():
    assert "Base.Hammer" not in items.FOOD_IDS
    assert items.use_of("Base.Hammer") != "food"
    assert items.use_of("Base.Hammer") == "weapon"


def test_a_vessel_holding_water_is_water_whatever_its_name():
    fc = sorted(i for i, it in DATA.items() if _water(it))
    assert fc
    for i in fc:
        assert items.use_of(i) == "water", i
    assert DATA["Base.WaterBottle"]["drinkable"] and items.use_of("Base.WaterBottle") == "water"


def test_a_disinfectant_a_bleach_a_beer_and_tainted_water_are_not_water():
    """PZA/1.4.1 (P24-F): F2's Disinfectant (RubbingAlcohol, drinkable in the dataset, no poison) read water and was
    drunk 68 times with no thirst fall; a bleach (Hazardous, a poison), a beer or a spirit (Alcoholic) and a dish of
    TaintedWater (Hazardous) are not water either (PZA/1.5)."""
    for i in ("Base.Disinfectant", "Base.Bleach", "Base.BeerCan", "Base.Vodka", "Base.WaterDish"):
        assert DATA[i]["drinkable"] and DATA[i]["fluid_ids"], i
        assert items.use_of(i) == "other", i
    assert "Base.Disinfectant" not in items.DRINK_IDS


def test_a_pop_a_juice_and_a_milk_are_water():
    """PZA/1.5 (the Task 9 amendment): a drinkable beverage that lowers thirst and harms nothing is water; the
    dataset's fluids carry the categories and the thirst change (Cola Beverage -30, CowMilk Beverage -50)."""
    for i in ("Base.JuiceBox", "Base.Milk", "Base.PopBottle"):
        assert items.use_of(i) == "water", i
    assert {"Cola", "CowMilk", "JuiceGrape"} <= items.DRINK_FLUIDS and "Beer" not in items.DRINK_FLUIDS
    assert "TaintedWater" not in items.DRINK_FLUIDS and "Bleach" not in items.DRINK_FLUIDS


def test_an_empty_vessel_is_a_container():
    """PZA/1.4.1: a drinking vessel spawning empty reads `container` (a saucepan too: the dataset's fallback has no
    weapon rule for it), never water; one over 3 litres (a bucket) is not one."""
    vessels = sorted(i for i, it in DATA.items() if _container(it))
    for i in ("Base.PopEmpty", "Base.Mugl", "Base.Bowl", "Base.GlassTumbler"):
        assert i in vessels and items.use_of(i) == "container", i
    for i in vessels:
        assert items.use_of(i) in ("container", "weapon", "bandage"), i
    assert items.VESSEL_IDS == frozenset(vessels) and not items.VESSEL_IDS & items.DRINK_IDS
    assert items.use_of("Base.BucketEmpty") == "other"


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


def test_a_drinkable_container_of_only_poisons_is_neither_water_nor_a_container():
    """Bleach, hair dye: drinkable containers in the dataset whose every fluid carries `poison` in `fluids`."""
    poison = sorted(i for i, it in DATA.items()
                    if it["kind"] == "fluid_container" and it.get("drinkable") and _poison_only(it))
    assert "Base.Bleach" in poison and any("HairDye" in i for i in poison), poison
    for i in poison:
        assert items.use_of(i) not in ("water", "container"), i


def test_an_empty_named_container_is_never_water():
    """PZA/1.4.1 (P24-F): an `Empty`-named container spawns empty, so it is a `container` when it is a drinking vessel,
    never water (Plan 23 read a drinkable one water whatever its fill)."""
    empties = sorted(i for i, it in DATA.items() if it["kind"] == "fluid_container" and i.endswith("Empty"))
    assert any(_container(DATA[i]) for i in empties), empties
    for i in empties:
        assert items.use_of(i) != "water", i
        assert (items.use_of(i) == "container") == _container(DATA[i]), i


def test_a_drainable_is_not_food_or_water():
    dr = sorted(i for i, it in DATA.items() if it["kind"] == "drainable")
    assert dr
    for i in dr:
        assert items.use_of(i) not in ("food", "water"), i


def test_a_sealed_pop_can_is_not_water():
    """PZA/1.5.1 (Task 9 review minor 2): `Base.Pop` and `Base.Pop2` spawn sealed (tagged base:sealedbeveragecan,
    canPlayerEmpty false), which vanilla's drink menu refuses: other, never water, though their Cola quenches."""
    for i in ("Base.Pop", "Base.Pop2"):
        assert "base:sealedbeveragecan" in DATA[i]["tags"] and set(DATA[i]["fluid_ids"]) <= items.DRINK_FLUIDS, i
        assert items.use_of(i) == "other" and i not in items.DRINK_IDS, i


def test_bandages_by_the_scripts_can_bandage_and_the_rest_other():
    """PZA/1.5.1 (Task 9 review minor 5): bandage is isCanBandage(), the script's CanBandage, as the Lua's W.useOf
    reads it: the rags rip makes and wash cleans (RippedSheets, RippedSheetsDirty) are bandages, a Rag is not."""
    for i in ("Base.Bandage", "Base.BandageDirty", "Base.RippedSheets", "Base.RippedSheetsDirty", "Base.DenimStrips"):
        assert items.use_of(i) == "bandage", i
    for i in ("Base.Rag", "Base.BandageBox", "Base.Nails"):
        assert items.use_of(i) == "other", i
    assert items.use_of(None) == "other" and items.use_of("") == "other"


def test_the_uses_are_the_six_names_the_schema_names():
    from agent.base import pza1
    assert items.USES == ("food", "water", "weapon", "bandage", "other", "container") == pza1.ITEM_USES


def test_pants_and_panties_are_not_weapons_by_the_rx():
    assert items.use_of("Base.Pants") == "other"
    assert items.use_of("Base.Pan") == "weapon"


# ================================================================ fix wave P (I-4)
def test_a_food_the_dataset_marks_cant_eat_is_other_never_food():
    """A sealed can (`CantEat = true`): vanilla's menu never offers its eat, so the planner never reads it food."""
    sealed = sorted(i for i, it in DATA.items() if it["kind"] == "food" and it.get("cant_eat"))
    assert "Base.TinnedBeans" in sealed and len(sealed) > 10, sealed
    for i in sealed:
        assert items.use_of(i) == "other", i
    assert items.FOOD_IDS == frozenset(i for i, it in DATA.items() if it["kind"] == "food" and not it.get("cant_eat"))
    assert items.use_of("Base.Apple") == "food" and not DATA["Base.Apple"].get("cant_eat")


def test_days_fresh_reads_the_dataset_and_none_for_a_name_it_does_not_carry():
    fresh = sorted(i for i, it in DATA.items() if it["kind"] == "food" and it.get("days_fresh") is not None)
    assert fresh
    for i in fresh[:20]:
        assert items.days_fresh(i) == DATA[i]["days_fresh"], i
    assert items.days_fresh("Base.NoSuchThing") is None and items.days_fresh(None) is None
