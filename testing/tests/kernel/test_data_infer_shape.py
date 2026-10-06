"""The generated inference templates (NR_Data_Infer.lua, Plan 6 Task 10, ruling 13) read back under Lua 5.1.

tools/food_nutrients.py --emit-infer writes the file from data/food-nutrients.json and data/food-items.json.
It is not a kernel file, so it is loaded on top of the session host the way test_data_nutrients_shape.py
loads the nutrient table; it reads only NutritionRevamp, which the host already has. The templates are
then driven through K.vector.infer, the kernel function the intake's fallback calls.
"""
import json
import math
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Data_Infer.lua")
NUTRIENTS_JSON = os.path.join(REPO, "data", "food-nutrients.json")
ITEMS_JSON = os.path.join(REPO, "data", "food-items.json")
MACROS = ("calories", "carbs", "lipids", "proteins")


@pytest.fixture(scope="module")
def infer_host(host):
    with open(DATA, encoding="utf-8") as fh:
        src = fh.read()
    host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@NR_Data_Infer.lua")()
    return host


@pytest.fixture(scope="module")
def templates(infer_host):
    return infer_host.py(infer_host.G.NutritionRevamp.data.infer)


@pytest.fixture(scope="module")
def food_types():
    with open(ITEMS_JSON, encoding="utf-8") as fh:
        items = json.load(fh)["items"]
    return {r["id"]: r.get("food_type") for r in items}


def _non_macro_keys(h):
    return [k for k in h.K.vector.KEYS.values() if k not in MACROS]


def test_default_is_present_over_every_mapped_food(templates):
    with open(NUTRIENTS_JSON, encoding="utf-8") as fh:
        data = json.load(fh)
    foods = [r for r in data["items"] if r["kind"] == "food" and r["fdc_id"] and r["basis"] == "per_item"]
    assert "_default" in templates
    assert templates["_default"]["n"] == len(foods)


def test_every_entry_carries_every_non_macro_key_finite_and_non_negative(infer_host, templates):
    keys = set(_non_macro_keys(infer_host))
    assert len(keys) == 27
    for food_type, entry in templates.items():
        assert set(entry) == {"n", "density"}, food_type
        assert entry["n"] >= 3, food_type
        assert set(entry["density"]) == keys, food_type
        for k, v in entry["density"].items():
            assert isinstance(v, (int, float)) and math.isfinite(v) and v >= 0, (food_type, k, v)


def test_every_type_is_a_food_type_the_dataset_spells(templates, food_types):
    spelled = set(t for t in food_types.values() if t)
    assert set(templates) - {"_default"} <= spelled


def test_the_apple_records_type_fruits_has_a_template(templates, food_types):
    assert food_types["Base.Apple"] == "Fruits"
    assert "Fruits" in templates
    assert templates["Fruits"]["density"]["vitC"] > 0


def test_the_tail_comment_states_the_counts(templates):
    with open(DATA, encoding="utf-8", newline="") as fh:
        src = fh.read()
    assert "\r" not in src
    assert src.endswith("\n-- %d types, _default over %d records\n" % (len(templates) - 1,
                                                                        templates["_default"]["n"]))


def test_the_densities_are_the_emitters(templates):
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import food_nutrients as fn
    with open(NUTRIENTS_JSON, encoding="utf-8") as fh:
        data = json.load(fh)
    want, _fallen = fn.infer_templates(data, fn.load_dataset())
    assert set(want) == set(templates)
    for food_type, entry in want.items():
        assert templates[food_type]["n"] == entry["n"]
        for k, v in entry["density"].items():
            assert templates[food_type]["density"][k] == v, (food_type, k)


def test_infer_through_the_loaded_templates(infer_host, templates):
    h = infer_host
    t = h.G.NutritionRevamp.data.infer
    macros = h.table({"calories": 100.0, "carbs": 25.0, "lipids": 0.3, "proteins": 0.5})
    v = h.py(h.K.vector.infer(macros, "Fruits", t))
    assert abs(v["vitC"] - templates["Fruits"]["density"]["vitC"] * 100.0) < 1e-9
    assert v["calories"] == 100.0
    v = h.py(h.K.vector.infer(macros, "Tea", t))                 # a fallen-back type: `_default`
    assert abs(v["iron"] - templates["_default"]["density"]["iron"] * 100.0) < 1e-9
