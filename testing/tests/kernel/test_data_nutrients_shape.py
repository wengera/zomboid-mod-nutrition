"""The generated nutrient table (NR_Data_Nutrients.lua, Plan 6 Task 9) read back under Lua 5.1.

tools/food_nutrients.py --emit-lua writes the file from data/food-nutrients.json. It is not a kernel file,
so it is loaded on top of the session host (NR_Core.lua and NR_Kernel_Vector.lua among the kernel files)
the way test_data_units.py loads it. The tables are file locals: the entry ids are enumerated off the
source text and every entry is read back through the loaders and compared with the JSON, key by key --
an item's four macros at the script block's two decimals (ruling T9-1), everything else exactly.
"""
import json
import math
import os
import re

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Data_Nutrients.lua")
NUTRIENTS_JSON = os.path.join(REPO, "data", "food-nutrients.json")

UNITS = {"calories": "kcal", "carbs": "g", "lipids": "g", "proteins": "g", "fibre": "g", "water": "g",
         "vitC": "mg", "iron": "mg", "phytate": "mg",
         "retinol": "ug", "carotene": "ug", "vitD": "ug", "vitE": "mg", "vitK": "ug", "thiamine": "mg",
         "riboflavin": "mg", "niacin": "mg", "vitB6": "mg", "folate": "ug", "vitB12": "ug", "choline": "mg",
         "sodium": "mg", "potassium": "mg", "calcium": "mg", "magnesium": "mg", "zinc": "mg", "iodine": "ug",
         "selenium": "ug", "efa": "g", "caffeine": "mg", "ethanol": "g"}


@pytest.fixture(scope="module")
def gen_host(host):
    with open(DATA, encoding="utf-8") as fh:
        src = fh.read()
    host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@NR_Data_Nutrients.lua")()
    return host


@pytest.fixture(scope="module")
def output():
    with open(NUTRIENTS_JSON, encoding="utf-8") as fh:
        return json.load(fh)


def _ids(block):
    with open(DATA, encoding="utf-8") as fh:
        src = fh.read()
    m = re.search(r"^local " + block + r" = \{\n(.*?)^\}", src, re.S | re.M)
    assert m is not None, block
    return re.findall(r'^    \["([^"]+)"\] = \{', m.group(1), re.M)


def _mapped(output):
    items = {r["pz_id"]: r["per_item"] for r in output["items"] if r["basis"] == "per_item" and r["fdc_id"]}
    fluids = {r["pz_id"]: r["per_litre"] for r in output["fluids"] if r["basis"] == "per_litre" and r["fdc_id"]}
    return items, fluids


def _keys(h):
    return list(h.K.vector.KEYS.values())


MACROS = ("calories", "carbs", "lipids", "proteins")


def _same(got, block, item=False):
    """Every key equal to the JSON's value (null read as 0) to 1e-9; an item's four macros equal to
    round(value, 2), the script block's value (ruling T9-1)."""
    for k, want in block.items():
        if item and k in MACROS and want is not None:
            want = round(want, 2)
        assert abs(got[k] - (0.0 if want is None else want)) <= 1e-9, (k, got[k], want)


def test_the_entry_counts_are_the_jsons_mapped_counts(output):
    items, fluids = _mapped(output)
    assert _ids("NUTRIENTS") == sorted(items)
    assert _ids("FLUIDS") == sorted(fluids)
    assert len(items) + len(fluids) == output["meta"]["counts"]["mapped"]


def test_the_tail_comment_states_the_counts(output):
    items, fluids = _mapped(output)
    with open(DATA, encoding="utf-8", newline="") as fh:
        src = fh.read()
    assert "\r" not in src
    assert src.endswith("\n-- %d items, %d fluids, 31 keys\n" % (len(items), len(fluids)))


@pytest.mark.parametrize("block,loader", [("NUTRIENTS", "nutrients"), ("FLUIDS", "fluids")])
def test_every_entry_carries_every_key_and_no_other_each_finite_and_non_negative(gen_host, block, loader):
    h = gen_host
    keys = set(_keys(h))
    get = h.G.NutritionRevamp.data[loader].get
    ids = _ids(block)
    assert ids
    for pz_id in ids:
        vec = h.py(get(pz_id))
        assert set(vec) == keys, pz_id
        for k, v in vec.items():
            assert isinstance(v, (int, float)) and math.isfinite(v) and v >= 0, (pz_id, k, v)


@pytest.mark.parametrize("block", ["NUTRIENTS", "FLUIDS"])
def test_every_entry_writes_every_key_in_the_vector_order(gen_host, block):
    keys = _keys(gen_host)
    with open(DATA, encoding="utf-8") as fh:
        src = fh.read()
    body = re.search(r"^local " + block + r" = \{\n(.*?)^\}", src, re.S | re.M).group(1)
    lines = [l for l in body.split("\n") if l.strip()]
    assert len(lines) == len(_ids(block))
    for line in lines:
        inner = re.match(r'^    \["[^"]+"\] = \{ (.*) \},  -- SOURCE \S+ (exact|close|proxy|guess)$', line)
        assert inner is not None, line[:80]
        assert re.findall(r"(\w+) = ", inner.group(1)) == keys


def test_every_value_is_the_jsons(gen_host, output):
    h = gen_host
    items, fluids = _mapped(output)
    for pz_id, block in items.items():
        _same(h.py(h.G.NutritionRevamp.data.nutrients.get(pz_id)), block, item=True)
    for name, block in fluids.items():
        _same(h.py(h.G.NutritionRevamp.data.fluids.get(name)), block)


def test_the_apple_entry_is_the_jsons_per_item(gen_host, output):
    rec = [r for r in output["items"] if r["pz_id"] == "Base.Apple"][0]
    got = gen_host.py(gen_host.G.NutritionRevamp.data.nutrients.get("Base.Apple"))
    assert set(got) == set(rec["per_item"])
    _same(got, rec["per_item"], item=True)
    assert got["calories"] == round(rec["per_item"]["calories"], 2)    # exactly the script block's value
    assert got["vitC"] == rec["per_item"]["vitC"]                       # a non-macro key round-trips exactly


def test_the_cola_fluid_is_the_jsons_per_litre(gen_host, output):
    rec = [r for r in output["fluids"] if r["pz_id"] == "Cola"][0]
    got = gen_host.py(gen_host.G.NutritionRevamp.data.fluids.get("Cola"))
    assert set(got) == set(rec["per_litre"])
    _same(got, rec["per_litre"])


def test_the_loader_returns_a_copy(gen_host):
    NR = gen_host.G.NutritionRevamp
    first = NR.data.nutrients.get("Base.Apple")
    want = first["calories"]
    first["calories"] = -1
    first["vitC"] = 12345
    second = NR.data.nutrients.get("Base.Apple")
    assert second["calories"] == want and second["vitC"] != 12345
    cola = NR.data.fluids.get("Cola")
    cola["water"] = -1
    assert NR.data.fluids.get("Cola")["water"] > 0


def test_an_absent_type_is_nil(gen_host, output):
    NR = gen_host.G.NutritionRevamp
    assert NR.data.nutrients.get("Base.Nonesuch") is None
    assert NR.data.fluids.get("Nonesuch") is None
    reasoned = [r["pz_id"] for r in output["items"] if r["basis"] == "none"]
    assert reasoned
    for pz_id in reasoned[:25]:
        assert NR.data.nutrients.get(pz_id) is None, pz_id


def test_the_units_are_unchanged(gen_host):
    assert dict(gen_host.G.NutritionRevamp.data.UNITS.items()) == UNITS
    assert set(UNITS) == set(_keys(gen_host))
