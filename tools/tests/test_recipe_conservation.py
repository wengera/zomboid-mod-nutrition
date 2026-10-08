"""tools/recipe_conservation.py (Plan 11 Task 16): the classes, recipe_scan's line accounting reused, the shipped data."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import recipe_conservation as rc  # noqa: E402


def food(cal, hunger=None, kind="food"):
    """A data/food-items.json row: kind, basis, the four macros and the script HungerChange the game loads."""
    return {"kind": kind, "nutrition_basis": "per_item", "calories": cal, "carbohydrates": cal / 10.0,
            "lipids": cal / 40.0, "proteins": cal / 20.0, "hunger_change": hunger}


FOOD = {"A": food(100.0), "B": food(60.0), "C": food(260.0), "D": food(100.0, hunger=-10.0), "E": food(50.0),
        "W": food(0.0, kind="drainable")}


def line(t, n, flags=("ItemCount",), mode=None, tags=()):
    fl = list(flags)
    return {"kind": "item", "amount": float(n), "variable": None, "types": [t] if t else [], "tags": list(tags),
            "categories": [], "mode": mode, "flags": fl, "mappers": [], "mapper": None, "overlayMapper": False,
            "extras": [], "consumed": mode != "keep", "amountIsItemCount": "ItemCount" in fl,
            "amountUses": None if "ItemCount" in fl else float(n), "subLines": [], "raw": "item %s [%s]" % (n, t)}


def recipe(name, ins, outs):
    return {"name": name, "inputs": ins, "outputs": [line(t, n, flags=()) for t, n in outs]}


def by_name(recipes):
    rows, skipped = rc.measure(recipes, FOOD)
    return {r["recipe"]: r for r in rows}, skipped


def test_the_classes():
    by, _ = by_name([
        recipe("make", [line("A", 1)], [("C", 1)]),                          # 100 -> 260
        recipe("cut", [line("C", 1)], [("A", 2)]),                           # 260 -> 200
        recipe("split", [line("C", 1)], [("A", 2), ("B", 1)]),               # 260 -> 260
        recipe("inherit", [line("A", 1, flags=("ItemCount", "InheritFood"))], [("C", 1)]),
    ])
    assert by["make"]["class"] == "creates" and by["make"]["ratio"] == 2.6
    assert by["cut"]["class"] == "destroys" and by["cut"]["ratio"] == round(200 / 260, 6)
    assert by["split"]["class"] == "conserves" and by["split"]["ratio"] == 1.0
    assert by["inherit"]["class"] == "inherits"
    assert by["make"]["macro_ratios"]["proteins"] == 2.6


def test_an_input_counts_uses_of_its_hunger_change():
    by, _ = by_name([recipe("uses", [line("D", 5, flags=())], [("E", 1)])])     # #0701: 5 of 10 points
    assert by["uses"]["kcal_in"] == 50.0 and by["uses"]["class"] == "conserves"


def test_a_food_with_no_hunger_change_costs_whole_items():
    by, _ = by_name([recipe("whole", [line("A", 2, flags=())], [("C", 1)])])     # #0702: 2 whole items
    assert by["whole"]["kcal_in"] == 200.0 and by["whole"]["class"] == "creates"


def test_a_destroy_line_is_charged_the_whole_item():
    by, _ = by_name([recipe("destroy", [line("D", 5, flags=(), mode="destroy")], [("E", 1)])])  # #0704
    assert by["destroy"]["kcal_in"] == 100.0 and by["destroy"]["class"] == "destroys"


def test_a_tool_costs_nothing():
    by, _ = by_name([recipe("tool", [line("C", 1, flags=(), mode="keep"), line("A", 1)], [("A", 1)])])  # #0699
    assert by["tool"]["kcal_in"] == 100.0 and by["tool"]["class"] == "conserves"


def test_the_unweighable_are_skipped_with_their_reason():
    _, skipped = by_name([
        recipe("tagged", [line(None, 1, tags=("base:meat",))], [("C", 1)]),
        recipe("unmapped", [line("Z", 1)], [("C", 1)]),
        recipe("drained", [line("W", 1, flags=())], [("A", 1)]),               # #0703: charged nothing
    ])
    assert skipped == {"tags-only": 1, "not-in-dataset": 1, "drainable": 1}


def test_creators_carry_the_scale_back_to_the_inputs():
    rows, _ = rc.measure([recipe("make", [line("A", 1)], [("C", 1)])], FOOD)
    assert rc.creators(rows) == {"make": 100.0 / 260.0}


def test_the_open_hotdog_pack_conserves_on_the_shipped_data():
    _files, rows, _skipped = rc.texts()
    by = {r["recipe"]: r for r in rows}
    assert by["OpenHotdogPack"]["class"] == "conserves", by["OpenHotdogPack"]


def test_the_written_files_are_in_sync():
    assert rc.main(["--check"]) == 0


# The Java craft OnCreate functions that write food values onto a created item (#3507; openMacAndCheese read
# on 42.21 for this task): the measurement weighs what the Java leaves, not the output script alone.

def java(name, ins, outs, fn, food_rows=None):
    r = recipe(name, ins, outs)
    r["onCreate"] = "RecipeCodeOnCreate." + fn
    return r


JFOOD = dict(FOOD, BIRD=food(1200.0, hunger=-160.0), LEG=food(200.0, hunger=-33.0),
             WING=food(150.0, hunger=-19.0), BREAST=food(250.0, hunger=-30.0),
             BOX=food(700.0), PASTA=dict(food(3360.0, hunger=-60.0), tags=["base:pasta", "base:driedfood"]),
             CHEESE=food(130.0, hunger=-14.0))


def jby(recipes):
    rows, skipped = rc.measure(recipes, JFOOD)
    return {r["recipe"]: r for r in rows}, skipped


def test_cut_chicken_scales_every_cut_by_the_birds_hunger_over_the_cuts():
    by, _ = jby([java("cut", [line("BIRD", 1)], [("LEG", 2), ("WING", 2), ("BREAST", 2)], "cutChicken")])
    scale = 160.0 / (2 * 33.0 + 2 * 19.0 + 2 * 30.0)
    assert by["cut"]["kcal_out"] == round(2 * (200.0 + 150.0 + 250.0) * scale, 3)
    assert by["cut"]["java"] == "RecipeCodeOnCreate.cutChicken"
    assert by["cut"]["class"] == "conserves"


def test_open_mac_and_cheese_leaves_a_sixth_of_the_pasta():
    by, _ = jby([java("open", [line("BOX", 1, flags=())], [("PASTA", 1), ("CHEESE", 1)], "openMacAndCheese")])
    assert by["open"]["kcal_out"] == round(3360.0 / 6 + 130.0, 3)
    assert by["open"]["class"] == "conserves"


def test_copy_food_values_from_list_inherits():
    by, _ = jby([java("omelette", [line("A", 1)], [("C", 1)], "makeOmelette"),
                 java("jar", [line("A", 1)], [("C", 1)], "makeJar")])
    assert by["omelette"]["class"] == "inherits" and by["jar"]["class"] == "inherits"


def test_make_coffee_keeps_the_output_macros():
    by, _ = jby([java("coffee", [line("A", 1)], [("C", 1)], "makeCoffee")])
    assert by["coffee"]["class"] == "creates" and by["coffee"]["kcal_out"] == 260.0


def test_an_unmodelled_java_writer_is_skipped():
    _, skipped = jby([java("fish", [line("A", 1)], [("C", 1)], "cutFish"),
                      java("small", [line("A", 1)], [("C", 1)], "cutSmallAnimal")])
    assert skipped == {"java-unmodelled": 2}


def test_a_split_is_one_consumed_input_into_several_items():
    by, _ = by_name([recipe("split", [line("C", 1, flags=(), mode="keep"), line("C", 1)], [("A", 2)]),
                     recipe("join", [line("A", 1), line("B", 1)], [("C", 1)]),
                     recipe("one", [line("A", 1)], [("A", 1)])])
    assert by["split"]["split"] is True and by["join"]["split"] is False and by["one"]["split"] is False


def test_the_shipped_data_conserves_the_hot_dog_the_patty_and_the_mac_and_cheese():
    _files, rows, _skipped = rc.texts()
    by = {r["recipe"]: r for r in rows}
    for name in ("MakeHotDog", "MakeMeatPatty", "open_mac_and_cheese"):
        assert by[name]["class"] == "conserves", by[name]


def test_the_one_creator_left_on_the_shipped_data_is_the_tortilla_chips():
    _files, rows, _skipped = rc.texts()
    assert sorted(rc.creators(rows)) == ["MakeTortillaChips"]


def test_the_json_carries_the_class_and_split_counts():
    import json
    rows, skipped = rc.measure([recipe("make", [line("A", 1)], [("C", 1)]),
                                recipe("split", [line("C", 1)], [("A", 2), ("B", 1)]),
                                recipe("cut", [line("C", 1)], [("A", 2)])], FOOD)
    meta = json.loads(rc.emit_json(rows, skipped))["meta"]
    assert meta["classes"] == {"conserves": 1, "creates": 1, "destroys": 1, "inherits": 0}
    assert meta["splits"] == {"conserves": 1, "creates": 0, "destroys": 1, "inherits": 0}


# Plan 11a Task 16 fix 1: a creator whose input spends fewer uses than the item holds is named, and the shipped
# hot dog and hotdog pack conserve on their corrected rows.

def test_a_creator_spending_part_of_an_input_carries_a_partial_use_note():
    by, _ = by_name([recipe("chips", [line("D", 1, flags=())], [("C", 1)]),        # 1 of D's 10 uses -> 260 kcal
                     recipe("whole", [line("A", 1)], [("C", 1)])])                  # an ItemCount line spends it all
    notes = [n for n in by["chips"]["notes"] if n.startswith("partial-use input")]
    assert by["chips"]["class"] == "creates"
    assert notes == ["partial-use input: D spends 1 of its 10 uses (no ItemCount flag, #0701), "
                     "so the craft charges 0.1 of the item"], by["chips"]["notes"]
    assert not [n for n in by["whole"]["notes"] if n.startswith("partial-use input")]


def test_a_partial_use_input_on_a_recipe_that_conserves_carries_no_note():
    by, _ = by_name([recipe("uses", [line("D", 5, flags=())], [("E", 1)])])
    assert by["uses"]["class"] == "conserves"
    assert not [n for n in by["uses"]["notes"] if n.startswith("partial-use input")]


def test_the_shipped_tortilla_chips_carry_the_partial_use_note_and_keep_their_factor():
    _files, rows, _skipped = rc.texts()
    chips = {r["recipe"]: r for r in rows}["MakeTortillaChips"]
    assert "partial-use input: Base.Tortilla spends 1 of its 5 uses (no ItemCount flag, #0701), so the craft " \
           "charges 0.2 of the item" in chips["notes"], chips["notes"]
    assert round(rc.creators(rows)["MakeTortillaChips"], 6) == 0.242611


def test_the_shipped_hot_dog_and_hotdog_pack_conserve_at_one():
    _files, rows, _skipped = rc.texts()
    by = {r["recipe"]: r for r in rows}
    assert by["OpenHotdogPack"]["ratio"] == 1.0, by["OpenHotdogPack"]
    assert abs(by["MakeHotDog"]["ratio"] - 1.0) < 0.001, by["MakeHotDog"]
