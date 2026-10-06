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


# Plan 4: the nine Plan 2 keys first in their order, then the twenty-two kinetics keys in the plan's order.
PLAN2_KEYS = ["calories", "carbs", "lipids", "proteins", "fibre", "water", "vitC", "iron", "phytate"]
PLAN4_KEYS = ["retinol", "carotene", "vitD", "vitE", "vitK", "thiamine", "riboflavin", "niacin", "vitB6",
              "folate", "vitB12", "choline", "sodium", "potassium", "calcium", "magnesium", "zinc", "iodine",
              "selenium", "efa", "caffeine", "ethanol"]


def test_keys_are_the_31_in_the_plan_order(host):
    keys = list(host.K.vector["keys"]().values())
    assert len(PLAN4_KEYS) == 22
    assert keys == PLAN2_KEYS + PLAN4_KEYS
    assert len(keys) == 31


def test_new_zeroes_every_one_of_the_31_keys(host):
    v = host.py(host.K.vector.new())
    assert len(v) == 31
    assert all(v[k] == 0 for k in PLAN4_KEYS)


def test_add_carries_a_new_key(host):
    dst = host.K.vector.new()
    host.K.vector.add(dst, host.table({"caffeine": 96.0, "ethanol": 39.5}), 0.5)
    assert abs(dst.caffeine - 48.0) < 1e-9
    assert abs(dst.ethanol - 19.75) < 1e-9
    assert dst.retinol == 0


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


def test_a_seed_vector_reads_back_its_new_keys(data_host):
    v = data_host.py(data_host.G.NutritionRevamp.data.nutrients.get("Base.Carrots"))
    assert len(v) == 31
    assert v["carotene"] > 1000          # micrograms of beta-carotene in a carrot
    assert v["caffeine"] == 0 and v["ethanol"] == 0


def test_unknown_type_is_nil(data_host):
    assert data_host.G.NutritionRevamp.data.nutrients.get("Base.Nonesuch") is None


def test_cola_is_per_litre(data_host):
    v = data_host.G.NutritionRevamp.data.fluids.get("Cola")
    assert lua51.lua_type(v) == "table"
    assert abs(v["calories"] - 436.8) < 1.0           # the generated table: FDC 174852 per litre (Plan 6)


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


# --- the four-source assembly (NR_Kernel_Vector.lua, pure, injected lookup) ---

# The Task 4 seed values, so the kernel assembly is exercised with no NR.data reference.
SEEDS = {
    "Base.Apple": {"calories": 95.0, "carbs": 25.13, "lipids": 0.31, "proteins": 0.47,
                   "fibre": 4.4, "water": 155.8, "vitC": 8.4, "iron": 0.22, "phytate": 0.0},
    "Base.Lettuce": {"calories": 54.0, "carbs": 10.33, "lipids": 0.54, "proteins": 4.9,
                     "fibre": 6.3, "water": 285.0, "vitC": 12.0, "iron": 3.0, "phytate": 0.0},
    "Base.Tomato": {"calories": 14.0, "carbs": 3.5, "lipids": 0.2, "proteins": 1.3,
                    "fibre": 0.94, "water": 73.7, "vitC": 10.7, "iron": 0.21, "phytate": 0.0},
    "Base.MincedMeat": {"calories": 300.0, "carbs": 0.0, "lipids": 30.0, "proteins": 46.0,
                        "fibre": 0.0, "water": 160.0, "vitC": 0.0, "iron": 4.0, "phytate": 0.0},
}
STEAK = {"calories": 220.0, "carbs": 0.0, "lipids": 9.35, "proteins": 31.62,
         "fibre": 0.0, "water": 74.0, "vitC": 0.0, "iron": 2.4, "phytate": 0.0}
COLA = {"calories": 400.0, "carbs": 104.0, "lipids": 0.0, "proteins": 0.0,
        "fibre": 0.0, "water": 890.0, "vitC": 0.0, "iron": 0.0, "phytate": 0.0}


@pytest.fixture
def lookup(host):
    # A Lua closure over a Lua table of a couple of known vectors; t[k] is nil for an absent key, so
    # the kernel's `missing` path is exercised with a type the table omits.
    seeds = host.table(SEEDS)
    return host.rt.eval("function(t) return function(k) return t[k] end end")(seeds)


def test_baseline_scales_a_type_by_its_share(host, lookup):
    vec, missing = host.K.vector.baseline(lookup, "Base.Apple", 0.5)
    v = host.py(vec)
    assert abs(v["calories"] - 47.5) < 1e-9
    assert abs(v["carbs"] - 12.565) < 1e-9
    assert abs(v["vitC"] - 4.2) < 1e-9
    assert list(host.py(missing).values()) == []


def test_baseline_missing_type_is_all_zero_and_named(host, lookup):
    vec, missing = host.K.vector.baseline(lookup, "Base.Nonesuch", 1)
    v = host.py(vec)
    for val in v.values():
        assert val == 0
    assert list(host.py(missing).values()) == ["Base.Nonesuch"]


def test_dish_scales_ingredient_sum_to_the_dish_macro_total(host, lookup):
    # Lettuce macro total 69.77 + Tomato 19.0 = 88.77; dishMacroTotal equal to it -> scale 1.0.
    vec, note = host.K.vector.dish(lookup, host.rt.table("Base.Lettuce", "Base.Tomato"), 88.77)
    v = host.py(vec)
    assert note["scaled"] is True
    assert abs(v["calories"] - 68.0) < 1e-6
    assert abs(v["vitC"] - 22.7) < 1e-6
    assert abs(v["carbs"] - 13.83) < 1e-6
    assert list(host.py(note["missing"]).values()) == []


def test_dish_half_macro_total_halves_every_key(host, lookup):
    vec, note = host.K.vector.dish(lookup, host.rt.table("Base.Lettuce", "Base.Tomato"), 88.77 / 2)
    v = host.py(vec)
    assert note["scaled"] is True
    assert abs(v["calories"] - 34.0) < 1e-6
    assert abs(v["vitC"] - 11.35) < 1e-6


def test_dish_zero_scratch_total_is_not_scaled(host, lookup):
    vec, note = host.K.vector.dish(lookup, host.rt.table("Base.Ghost1", "Base.Ghost2"), 50.0)
    v = host.py(vec)
    assert note["scaled"] is False
    for val in v.values():
        assert val == 0
    assert sorted(host.py(note["missing"]).values()) == ["Base.Ghost1", "Base.Ghost2"]


def test_meat_scales_baseline_by_raw_over_base_hunger(host):
    steak = host.table(STEAK)
    vec = host.K.vector.meat(steak, -0.44, -0.40)
    v = host.py(vec)
    assert abs(v["calories"] - 242.0) < 1e-6
    assert abs(v["proteins"] - 34.782) < 1e-6


def test_meat_zero_base_hunger_keeps_scale_one(host):
    steak = host.table(STEAK)
    vec = host.K.vector.meat(steak, -0.44, 0)
    v = host.py(vec)
    assert abs(v["calories"] - 220.0) < 1e-6


def test_craft_sums_each_consumed_type_by_count_and_share(host, lookup):
    # MakeMeatPatty: 40 USES of ONE tub (#0745); the map counts consumed INSTANCES, so it reads 1
    vec, missing = host.K.vector.craft(lookup, host.table({"Base.MincedMeat": 1}), 1)
    v = host.py(vec)
    assert abs(v["calories"] - 300.0) < 1e-6
    assert abs(v["proteins"] - 46.0) < 1e-6
    assert list(host.py(missing).values()) == []


def test_craft_multiplies_by_the_instance_count(host, lookup):
    vec, missing = host.K.vector.craft(lookup, host.table({"Base.MincedMeat": 2}), 0.5)
    v = host.py(vec)
    assert abs(v["calories"] - 300.0) < 1e-6
    assert abs(v["proteins"] - 46.0) < 1e-6


def test_craft_names_a_missing_type_and_still_adds_the_rest(host, lookup):
    counts = host.table({"Base.MincedMeat": 1, "Base.Nonesuch": 2})
    vec, missing = host.K.vector.craft(lookup, counts, 1)
    v = host.py(vec)
    assert abs(v["calories"] - 300.0) < 1e-6
    assert list(host.py(missing).values()) == ["Base.Nonesuch"]


def test_fluid_scales_the_per_litre_vector_by_litres(host):
    cola = host.table(COLA)
    vec = host.K.vector.fluid(cola, 0.3)
    v = host.py(vec)
    assert abs(v["calories"] - 120.0) < 1e-6
    assert abs(v["carbs"] - 31.2) < 1e-6


# --- the fallback inference and the declared-nutrients contract (Plan 6 Task 10, rulings 13-14) ---

# A synthetic template: two types and `_default`, densities per kcal on a few keys (the rest absent).
TEMPLATES = {
    "Fruits": {"n": 3, "density": {"fibre": 0.04, "water": 1.5, "vitC": 0.1, "iron": 0.002}},
    "Meat": {"n": 4, "density": {"fibre": 0.0, "water": 0.3, "iron": 0.01, "vitB12": 0.005}},
    "_default": {"n": 9, "density": {"fibre": 0.01, "water": 0.5, "vitC": 0.02, "iron": 0.005}},
}
APPLE_MACROS = {"calories": 100.0, "carbs": 25.0, "lipids": 0.3, "proteins": 0.5}


def _infer(host, macros, food_type, templates=TEMPLATES):
    t = None if templates is None else host.table(templates)
    return host.py(host.K.vector.infer(host.table(macros), food_type, t))


def test_infer_copies_the_macros_and_multiplies_the_type_density_by_calories(host):
    v = _infer(host, APPLE_MACROS, "Fruits")
    assert len(v) == 31
    assert (v["calories"], v["carbs"], v["lipids"], v["proteins"]) == (100.0, 25.0, 0.3, 0.5)
    assert abs(v["fibre"] - 4.0) < 1e-9
    assert abs(v["water"] - 150.0) < 1e-9
    assert abs(v["vitC"] - 10.0) < 1e-9
    assert abs(v["iron"] - 0.2) < 1e-9
    assert v["vitB12"] == 0                       # a key the template does not carry stays 0


def test_infer_picks_the_template_of_the_food_type(host):
    v = _infer(host, APPLE_MACROS, "Meat")
    assert abs(v["iron"] - 1.0) < 1e-9
    assert abs(v["vitB12"] - 0.5) < 1e-9
    assert v["vitC"] == 0


def test_infer_an_unknown_type_falls_back_to_default(host):
    v = _infer(host, APPLE_MACROS, "Insect")
    assert abs(v["fibre"] - 1.0) < 1e-9
    assert abs(v["vitC"] - 2.0) < 1e-9


def test_infer_a_nil_type_takes_default(host):
    v = _infer(host, APPLE_MACROS, None)
    assert abs(v["water"] - 50.0) < 1e-9


def test_infer_zero_calories_is_the_macros_only(host):
    v = _infer(host, {"calories": 0.0, "carbs": 2.0, "lipids": 0.0, "proteins": 1.0}, "Fruits")
    assert (v["calories"], v["carbs"], v["proteins"]) == (0.0, 2.0, 1.0)
    assert all(v[k] == 0 for k in v if k not in ("carbs", "proteins"))


def test_infer_a_missing_macro_reads_zero(host):
    v = _infer(host, {"calories": 10.0}, "Fruits")
    assert v["carbs"] == 0 and v["lipids"] == 0 and v["proteins"] == 0
    assert abs(v["fibre"] - 0.4) < 1e-9


def test_infer_without_templates_or_default_is_the_macros_only(host):
    v = _infer(host, APPLE_MACROS, "Fruits", templates=None)
    assert v["calories"] == 100.0 and v["fibre"] == 0
    v = _infer(host, APPLE_MACROS, "Insect", templates={"Fruits": TEMPLATES["Fruits"]})
    assert v["calories"] == 100.0 and v["fibre"] == 0


def test_infer_returns_a_fresh_vector(host):
    t = host.table(TEMPLATES)
    a = host.K.vector.infer(host.table(APPLE_MACROS), "Fruits", t)
    a.fibre = 999
    b = host.py(host.K.vector.infer(host.table(APPLE_MACROS), "Fruits", t))
    assert abs(b["fibre"] - 4.0) < 1e-9
    assert t["Fruits"]["density"]["fibre"] == 0.04


def _declared(host, text):
    vec, extra = host.K.vector.declared(text)
    return (None if vec is None else host.py(vec)), (extra if isinstance(extra, str) or extra is None
                                                     else list(host.py(extra).values()))


def test_declared_parses_the_units_contract_string(host):
    v, unknown = _declared(host, "fibre:12;vitC:3")
    assert len(v) == 31
    assert v["fibre"] == 12 and v["vitC"] == 3
    assert v["calories"] == 0 and v["carbs"] == 0           # macros absent: 0, the caller fills them
    assert unknown == []


def test_declared_with_no_known_key_falls_through(host):
    # the Task 10 review: a declaration made only of unknown keys must not land a zero vector over the table
    v, reason = _declared(host, "omega9:1;unobtainium:2")
    assert v is None and "no known key" in reason


def test_declared_takes_the_macros_when_given_and_tolerates_spaces_and_a_trailing_semicolon(host):
    v, unknown = _declared(host, " calories: 120.5 ; carbs:30;proteins:2.5;lipids:0;iron:1e-1 ;")
    assert (v["calories"], v["carbs"], v["proteins"], v["lipids"]) == (120.5, 30, 2.5, 0)
    assert abs(v["iron"] - 0.1) < 1e-12
    assert unknown == []


def test_declared_skips_and_reports_an_unknown_key(host):
    v, unknown = _declared(host, "fibre:13;vitZ:4;omega9:1")
    assert v["fibre"] == 13
    assert "vitZ" not in v
    assert unknown == ["vitZ", "omega9"]


@pytest.mark.parametrize("text", ["fibre:twelve;vitC:3", "fibre:-1", "fibre", "fibre:12;vitC",
                                  "fibre:nan", "fibre:inf", ":3", "fibre:", "", ";", 12])
def test_declared_a_malformed_string_is_nil_with_a_reason(host, text):
    v, reason = _declared(host, text)
    assert v is None
    assert isinstance(reason, str) and reason != ""
