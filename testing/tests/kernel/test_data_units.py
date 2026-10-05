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
    assert len(_seed_ids("NUTRIENTS")) == 8
    assert len(_seed_ids("FLUIDS")) == 3


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
