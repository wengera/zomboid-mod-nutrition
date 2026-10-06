"""The units contract of the nutrient data table (NR_Data_Nutrients.lua, NR.data.UNITS).

The kernel's coefficients assume one unit per vector key: K.stomach.ironFactor applies its
per-MILLIGRAM phytate and vitamin C slopes to the emptied vector unconverted, so a seed phytate in
grams reads about 1000x too weak an inhibition. NR.data.UNITS pins the interface Plan 6's pipeline
emits; these tests hold the table to it. Since Plan 6 Task 9 the file is GENERATED from
data/food-nutrients.json (tools/food_nutrients.py --emit-lua), so the pins below read the JSON rather than
the Plan 2 seed's hand values; test_data_nutrients_shape.py compares every entry with the JSON.
NR_Data_Nutrients.lua is not a kernel file, so it is loaded on top of the session host the way
test_kernel_vector.py loads it. The tables are file locals, so the entries are enumerated off the source
text and read back through the loaders.
"""
import json
import math
import os
import re
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA = os.path.join(
    REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Data_Nutrients.lua"
)
NUTRIENTS_JSON = os.path.join(REPO, "data", "food-nutrients.json")


def _output():
    with open(NUTRIENTS_JSON, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def units_host(host):
    with open(DATA, encoding="utf-8") as fh:
        src = fh.read()
    host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@NR_Data_Nutrients.lua")()
    return host


def _seed_ids(block):
    """The quoted keys of one local seed table (NUTRIENTS or FLUIDS) in the data file's source."""
    with open(DATA, encoding="utf-8") as fh:
        src = fh.read()
    m = re.search(r"^local " + block + r" = \{\n(.*?)^\}", src, re.S | re.M)
    assert m is not None, block
    return re.findall(r'^\s*\["([^"]+)"\] = \{', m.group(1), re.M)


def test_units_cover_every_vector_key_and_nothing_else(units_host):
    h = units_host
    units = dict(h.G.NutritionRevamp.data.UNITS.items())
    keys = set(h.K.vector.KEYS.values())
    assert set(units.keys()) == keys


@pytest.mark.parametrize("key", ["phytate", "vitC", "iron"])
def test_the_iron_interaction_keys_are_milligrams(units_host, key):
    assert units_host.G.NutritionRevamp.data.UNITS[key] == "mg"


def test_the_seed_tables_are_enumerated():
    out = _output()
    assert len(_seed_ids("NUTRIENTS")) == sum(1 for r in out["items"] if r["basis"] == "per_item")
    assert len(_seed_ids("FLUIDS")) == sum(1 for r in out["fluids"] if r["basis"] == "per_litre")


# Plan 4: the unit of every key (ug = micrograms, per item, per litre for a fluid).
UNITS = {"calories": "kcal", "carbs": "g", "lipids": "g", "proteins": "g", "fibre": "g", "water": "g",
         "vitC": "mg", "iron": "mg", "phytate": "mg",
         "retinol": "ug", "carotene": "ug", "vitD": "ug", "vitE": "mg", "vitK": "ug", "thiamine": "mg",
         "riboflavin": "mg", "niacin": "mg", "vitB6": "mg", "folate": "ug", "vitB12": "ug", "choline": "mg",
         "sodium": "mg", "potassium": "mg", "calcium": "mg", "magnesium": "mg", "zinc": "mg", "iodine": "ug",
         "selenium": "ug", "efa": "g", "caffeine": "mg", "ethanol": "g"}


def test_units_name_the_unit_of_every_key(units_host):
    assert dict(units_host.G.NutritionRevamp.data.UNITS.items()) == UNITS
    assert len(UNITS) == 31


def _seed_entries(block):
    """{pz_id: [the key names written in the entry's source text]} for one local seed table."""
    with open(DATA, encoding="utf-8") as fh:
        src = fh.read()
    m = re.search(r"^local " + block + r" = \{\n(.*?)^\}", src, re.S | re.M)
    body = re.sub(r"--[^\n]*", "", m.group(1))
    out = {}
    for pz_id, inner in re.findall(r'\["([^"]+)"\] = \{(.*?)\}', body, re.S):
        out[pz_id] = re.findall(r"(\w+) = ", inner)
    return out


@pytest.mark.parametrize("block", ["NUTRIENTS", "FLUIDS"])
def test_every_seed_entry_writes_every_key_explicitly(block):
    entries = _seed_entries(block)
    assert len(entries) == len(_seed_ids(block))
    for pz_id, names in entries.items():
        assert sorted(names) == sorted(UNITS), pz_id     # each key once, none missing, none extra


@pytest.mark.parametrize("block,loader", [("NUTRIENTS", "nutrients"), ("FLUIDS", "fluids")])
def test_every_seed_value_is_finite_and_non_negative(units_host, block, loader):
    get = units_host.G.NutritionRevamp.data[loader].get
    for pz_id in _seed_ids(block):
        vec = units_host.py(get(pz_id))
        for k, val in vec.items():
            assert math.isfinite(val) and val >= 0, (pz_id, k, val)


def _fluid(h, name):
    return h.py(h.G.NutritionRevamp.data.fluids.get(name))


def test_the_fluid_seeds_per_litre(units_host):
    h = units_host
    per_litre = dict((r["pz_id"], r["per_litre"]) for r in _output()["fluids"] if r["basis"] == "per_litre")
    for name in ("Water", "Cola", "JuiceGrape", "Beer", "Coffee", "Whiskey"):
        got = _fluid(h, name)
        for k, want in per_litre[name].items():
            assert got[k] == (0 if want is None else want), (name, k)
    water = _fluid(h, "Water")
    assert 990 < water["water"] <= 1000 and water["calories"] == 0      # grams of water in a litre
    beer = _fluid(h, "Beer")
    assert abs(beer["ethanol"] - 1000 * 0.05 * 0.789) < 1e-9          # 5 % ABV x 0.789 g/mL (ruling 7)
    whiskey = _fluid(h, "Whiskey")
    assert abs(whiskey["ethanol"] - 1000 * 0.40 * 0.789) < 1e-9       # 40 % ABV
    assert 300 < _fluid(h, "Coffee")["caffeine"] < 600                 # mg per litre of brewed coffee
    assert 500 < _fluid(h, "JuiceGrape")["potassium"] < 2000            # mg per litre, not g or ug
    for name in ("Water", "Cola", "JuiceGrape", "Coffee"):
        assert _fluid(h, name)["ethanol"] == 0


def test_the_vitamin_pill_has_no_entry(units_host):
    # Plan 6 maps the pills as tobacco_or_drug (no composition): the seed's 50 mg caffeine judgement is gone
    rec = [r for r in _output()["items"] if r["pz_id"] == "Base.PillsVitamins"][0]
    assert rec["basis"] == "none" and rec["no_nutrition_reason"] == "tobacco_or_drug"
    assert units_host.G.NutritionRevamp.data.nutrients.get("Base.PillsVitamins") is None


@pytest.mark.parametrize("pz_id", ["Base.Apple", "Base.Steak", "Base.Bread", "Base.Carrots", "Base.Lettuce",
                                   "Base.Tomato", "Base.MincedMeat", "Base.MeatPatty"])
def test_the_session_foods_carry_the_kinetics_keys(units_host, pz_id):
    v = units_host.py(units_host.G.NutritionRevamp.data.nutrients.get(pz_id))
    for k in ("potassium", "magnesium", "thiamine", "riboflavin", "niacin", "folate"):
        assert v[k] > 0, (pz_id, k)
    assert v["caffeine"] == 0 and v["ethanol"] == 0
    assert v["potassium"] < 2000 and v["sodium"] < 2000              # mg per item, not g or ug


def test_the_seed_magnitudes_sit_in_their_units(units_host):
    get = units_host.G.NutritionRevamp.data.nutrients.get
    carrot = units_host.py(get("Base.Carrots"))
    steak = units_host.py(get("Base.Steak"))
    bread = units_host.py(get("Base.Bread"))
    lettuce = units_host.py(get("Base.Lettuce"))
    assert 1000 < carrot["carotene"] < 20000         # ug beta-carotene in one carrot
    assert 0.5 < steak["vitB12"] < 10                # ug B12 in a steak
    assert 1 < steak["zinc"] < 20                    # mg zinc in a steak
    assert 500 < bread["sodium"] < 2000              # mg sodium in a loaf portion
    assert 100 < lettuce["vitK"] < 1000              # ug vitamin K in a romaine head
    assert carrot["vitB12"] == 0 and lettuce["vitB12"] == 0


@pytest.mark.parametrize("block,loader", [("NUTRIENTS", "nutrients"), ("FLUIDS", "fluids")])
def test_every_seed_phytate_is_zero_or_milligram_scale(units_host, block, loader):
    get = units_host.G.NutritionRevamp.data[loader].get
    for pz_id in _seed_ids(block):
        vec = get(pz_id)
        assert vec is not None, pz_id
        # the smallest mapped items (a maki roll, 3.6 mg) are single milligrams; a gram reading would be ~0.004
        assert vec["phytate"] == 0 or vec["phytate"] >= 1, (pz_id, vec["phytate"])


def test_a_legume_phytate_is_milligrams(units_host):
    # the dried legumes carry grams of phytic acid per bag: in milligrams, thousands (in grams it would read ~12)
    vec = units_host.G.NutritionRevamp.data.nutrients.get("Base.DriedLentils")
    assert 1000 < vec["phytate"] < 20000


def test_a_bread_sized_phytate_bites_through_the_iron_factor(units_host):
    # exp(-0.0034 x 400) = exp(-1.36) ~ 0.2567: the mg pin makes the inhibition real (in grams,
    # 0.4 would read ~0.999)
    f = units_host.K.stomach.ironFactor(400, 0)
    assert abs(f - math.exp(-1.36)) < 1e-9
    assert abs(f - 0.257) < 1e-3
