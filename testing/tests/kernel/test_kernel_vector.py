"""The nutrient-vector schema (NR_Kernel_Vector.lua) and the seed data table (NR_Data_Nutrients.lua).

NR_Kernel_Vector.lua is a kernel file: the session host loads it through its NR_Kernel* glob, so the
`host` fixture already has NutritionRevamp.kernel.vector. NR_Data_Nutrients.lua is NOT a kernel file
(its name is NR_Data*, not NR_Kernel*), so the host does not auto-load it; this test loads it on top
of the session host the way test_bench.py loads NR_Server_Bench.lua. The data file reads only
NutritionRevamp.kernel.vector, which the host already has, so it loads with no engine.
"""
import os
import pytest
import lupa.lua51 as lua51

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA = os.path.join(
    REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Data_Nutrients.lua"
)


@pytest.fixture(scope="session")
def data_host(host):
    with open(DATA, encoding="utf-8") as fh:
        src = fh.read()
    chunk = host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@NR_Data_Nutrients.lua")
    chunk()
    return host


# --- the vector schema (NR_Kernel_Vector.lua, loaded by the host glob) ---

def test_new_is_zeroed_over_every_declared_key(host):
    v = host.py(host.K.vector.new())
    keys = list(host.K.vector["keys"]().values())
    assert set(v.keys()) == set(keys)
    for val in v.values():
        assert val == 0


def test_macros_are_the_four_in_order(host):
    assert list(host.K.vector.MACROS.values()) == ["calories", "carbs", "lipids", "proteins"]


def test_keys_cover_the_macros_and_the_seed_mod_nutrients(host):
    keys = list(host.K.vector["keys"]().values())
    for k in ["calories", "carbs", "lipids", "proteins", "fibre", "water", "vitC", "iron", "phytate"]:
        assert k in keys


def test_add_accumulates_with_scale(host):
    dst = host.K.vector.new()
    src = host.table({"calories": 10, "carbs": 5})
    host.K.vector.add(dst, src, 2)
    host.K.vector.add(dst, src, 1)
    d = host.py(dst)
    assert d["calories"] == 30
    assert d["carbs"] == 15
    assert d["iron"] == 0


def test_add_returns_the_same_table_object(host):
    # lupa wraps each return in a fresh proxy, so identity is checked on the Lua side.
    same = host.rt.eval(
        "function() local K = NutritionRevamp.kernel local d = K.vector.new() return K.vector.add(d, {calories=1}, 1) == d end"
    )()
    assert same is True


# --- the seed loader (NR_Data_Nutrients.lua) ---

def test_apple_loads_with_macros_and_a_mod_nutrient(data_host):
    v = data_host.G.NutritionRevamp.data.nutrients.get("Base.Apple")
    assert lua51.lua_type(v) == "table"
    assert abs(v["calories"] - 95.0) < 0.5
    assert v["vitC"] is not None
    assert v["vitC"] > 0


def test_every_declared_key_is_present_on_a_seed_vector(data_host):
    v = data_host.py(data_host.G.NutritionRevamp.data.nutrients.get("Base.Steak"))
    keys = list(data_host.K.vector["keys"]().values())
    assert set(v.keys()) == set(keys)


def test_unknown_type_is_nil(data_host):
    assert data_host.G.NutritionRevamp.data.nutrients.get("Base.Nonesuch") is None


def test_cola_is_per_litre(data_host):
    v = data_host.G.NutritionRevamp.data.fluids.get("Cola")
    assert lua51.lua_type(v) == "table"
    assert abs(v["calories"] - 400.0) < 1.0


def test_unknown_fluid_is_nil(data_host):
    assert data_host.G.NutritionRevamp.data.fluids.get("Nonesuch") is None


def test_get_returns_a_fresh_copy_that_cannot_mutate_the_seed(data_host):
    NR = data_host.G.NutritionRevamp
    first = NR.data.nutrients.get("Base.Apple")
    first["calories"] = -1
    first["vitC"] = -1
    second = NR.data.nutrients.get("Base.Apple")
    assert abs(second["calories"] - 95.0) < 0.5
    assert second["vitC"] > 0
