"""The units contract of the seed data table (NR_Data_Nutrients.lua, NR.data.UNITS).

The kernel's coefficients assume one unit per vector key: K.stomach.ironFactor applies its
per-MILLIGRAM phytate and vitamin C slopes to the emptied vector unconverted, so a seed phytate in
grams reads about 1000x too weak an inhibition. NR.data.UNITS pins the interface Plan 6's pipeline
emits; these tests hold the seed to it. NR_Data_Nutrients.lua is not a kernel file, so it is loaded on
top of the session host the way test_kernel_vector.py loads it. The seed tables are file locals, so
the seed entries are enumerated off the source text and read back through the loaders.
"""
import math
import os
import re
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA = os.path.join(
    REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Data_Nutrients.lua"
)


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
    assert len(_seed_ids("NUTRIENTS")) == 9
    assert len(_seed_ids("FLUIDS")) == 6


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
    water = _fluid(h, "Water")
    assert water["water"] == 1000 and all(v == 0 for k, v in water.items() if k != "water")
    cola = _fluid(h, "Cola")
    assert (cola["water"], cola["sodium"], cola["caffeine"]) == (890, 40, 96)
    grape = _fluid(h, "JuiceGrape")
    assert (grape["water"], grape["potassium"]) == (840, 1320)
    beer = _fluid(h, "Beer")
    assert (beer["water"], beer["ethanol"], beer["potassium"]) == (920, 39.5, 270)
    assert abs(beer["ethanol"] - 1000 * 0.05 * 0.789) < 0.06        # 5 % ABV x 0.789 g/mL
    coffee = _fluid(h, "Coffee")
    assert (coffee["water"], coffee["caffeine"]) == (990, 428)
    assert abs(coffee["caffeine"] - 107 / 0.25) < 1e-9                # S0797: 107 mg per 250 mL
    whiskey = _fluid(h, "Whiskey")
    assert whiskey["ethanol"] == 315.6
    assert abs(whiskey["ethanol"] - 1000 * 0.40 * 0.789) < 1e-9      # 40 % ABV
    for name in ("Water", "Cola", "JuiceGrape", "Coffee"):
        assert _fluid(h, name)["ethanol"] == 0


def test_the_vitamin_pill_is_a_caffeine_item(units_host):
    pill = units_host.py(units_host.G.NutritionRevamp.data.nutrients.get("Base.PillsVitamins"))
    assert pill["caffeine"] == 50
    assert all(v == 0 for k, v in pill.items() if k != "caffeine")


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
        assert vec["phytate"] == 0 or vec["phytate"] >= 100, (pz_id, vec["phytate"])


def test_bread_phytate_is_milligrams(units_host):
    vec = units_host.G.NutritionRevamp.data.nutrients.get("Base.Bread")
    assert vec["phytate"] == 400


def test_a_bread_sized_phytate_bites_through_the_iron_factor(units_host):
    # exp(-0.0034 x 400) = exp(-1.36) ~ 0.2567: the mg pin makes the inhibition real (in grams,
    # 0.4 would read ~0.999)
    f = units_host.K.stomach.ironFactor(400, 0)
    assert abs(f - math.exp(-1.36)) < 1e-9
    assert abs(f - 0.257) < 1e-3
