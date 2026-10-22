"""Plan 19 Task 3d (wave W7): the stomach and satiety dials resolve from NR_Data_Dials.lua.

Each kernel field holds its registry row's value, and every moved value, every table's `pairs` order, the derived full
sleep debt and the two factors whose inline magnitudes became dials (the meal iron factor's slopes and band, the fat
factor's floor) read exactly as the code they replaced. The meal pool's request level satiety.MEAL_REQ is the fed
threshold hungerCurve.FED_M through `same` (one dial, the row carrying the joint fit); the appetite traits and the
nicotine withdrawal cap are fixed vanilla rows. A registry-only edit, made before the kernels load with no code change,
moves a kernel output (the mutation probes, dial-inventory section 3.4).
"""
import math
import os
import sys

import lupa.lua51 as lua51
import pytest

from .conftest import CORE, DIALS, REPO, kernel_files

sys.path.insert(0, os.path.join(REPO, "tools"))
import dials  # noqa: E402

DOMAINS = ("stomach", "satiety")
JOINT_FIT = ("satiety.W_PROTEIN", "satiety.W_FAT", "satiety.MEAL_HALF_LIFE_H", "satiety.MEAL_STEEP",
             "satiety.FULL_WEIGHT", "satiety.LIQUID_WEIGHT", "satiety.PROTEIN_FILL", "hungerCurve.FED_M")
DIVISORS = ("stomach.FAT_EFOLD_G", "stomach.WATER_HALF_MIN", "stomach.CAPACITY_MAX_G", "satiety.MEAL_HALF_LIFE_H",
            "satiety.MEAL_STEEP", "satiety.ACUTE_HALF_LIFE_H", "satiety.ACUTE_DECAY_HALF_LIFE_H",
            "satiety.NIC_FADE_DAYS")
FIXED = {"satiety.HEARTY": "vanilla #0485", "satiety.LIGHT": "vanilla #0485", "satiety.NIC_WITHDRAWAL_MAX": "vanilla #3632",
         "satiety.DISCOMFORT_MAX": "vanilla #3600"}

# The replaced constructors, verbatim from 6eede24a (the values and the assignment order the pairs order follows), and
# the two factors whose inline magnitudes moved to fields.
OLD = """
local O = { stomach = {}, satiety = {} }
O.stomach.BIOAVAIL = {}
O.stomach.BIOAVAIL.water = 1.0
O.stomach.BIOAVAIL.fibre = 1.0
O.stomach.BIOAVAIL.vitC = 0.85
O.stomach.BIOAVAIL.iron = 0.18
O.stomach.BIOAVAIL.phytate = 0.0
O.stomach.BIOAVAIL.retinol = 1.0
O.stomach.BIOAVAIL.carotene = 0.14
O.stomach.BIOAVAIL.vitD = 1.0
O.stomach.BIOAVAIL.vitE = 1.0
O.stomach.BIOAVAIL.vitK = 1.0
O.stomach.BIOAVAIL.thiamine = 1.0
O.stomach.BIOAVAIL.riboflavin = 1.0
O.stomach.BIOAVAIL.niacin = 1.0
O.stomach.BIOAVAIL.vitB6 = 1.0
O.stomach.BIOAVAIL.folate = 1.0
O.stomach.BIOAVAIL.vitB12 = 1.0
O.stomach.BIOAVAIL.choline = 1.0
O.stomach.BIOAVAIL.sodium = 1.0
O.stomach.BIOAVAIL.potassium = 1.0
O.stomach.BIOAVAIL.calcium = 0.25
O.stomach.BIOAVAIL.magnesium = 0.325
O.stomach.BIOAVAIL.zinc = 1.0
O.stomach.BIOAVAIL.iodine = 1.0
O.stomach.BIOAVAIL.selenium = 1.0
O.stomach.BIOAVAIL.efa = 1.0
O.stomach.VITD_FAT_FREE = 0.76
O.stomach.FAT_EFOLD_G = 3
O.stomach.RATE_BASE = 1.25
O.stomach.RATE_PER_KCAL = 0.0025
O.stomach.WATER_HALF_MIN = 13
O.stomach.LIQUID_PER_KCAL = 0.12
O.stomach.CAPACITY_MAX_G = 730
O.stomach.CAPACITY_HARD_G = 1100
O.satiety.HEARTY = 1.5
O.satiety.LIGHT = 0.75
O.satiety.W_PROTEIN = 2.49782
O.satiety.W_CARB = 1
O.satiety.W_FAT = 0.878683
O.satiety.W_NEUTRAL = 1
O.satiety.MEAL_HALF_LIFE_H = 0.583749
O.satiety.MEAL_REQ = 3.80654
O.satiety.MEAL_STEEP = 0.0356875
O.satiety.MEAL_SEED_MAX = 1180
O.satiety.FULL_WEIGHT = 0.517741
O.satiety.LIQUID_WEIGHT = 0.278815
O.satiety.BETA = 0.05
O.satiety.PROTEIN_FILL = 7.91676
O.satiety.DISCOMFORT_MAX = 100
O.satiety.ATWATER_P = 4
O.satiety.ATWATER_C = 4
O.satiety.ATWATER_F = 9
O.satiety.CIRCADIAN_A = 0.085
O.satiety.CIRCADIAN_PEAK_H = 19.8333
O.satiety.ACUTE_MAX = 0.7
O.satiety.ACUTE_HALF_LIFE_H = 0.5
O.satiety.ACUTE_DECAY_HALF_LIFE_H = 0.15
O.satiety.ACUTE_KIND = {}
O.satiety.ACUTE_KIND.aerobic = 1
O.satiety.ACUTE_KIND.resistance = 0.5
O.satiety.ACUTE_KIND.walk = 0
O.satiety.SLEEP_MAX = 0.18
O.satiety.SLEEP_DEBT_FULL_H = 2
O.satiety.NIC_MAX = 0.1313
O.satiety.NIC_FADE_DAYS = 182
O.satiety.NIC_WITHDRAWAL_MAX = 0.51
local K = NutritionRevamp.kernel
function O.ironFactor(phytateMg, vitCMg)
    return K.clamp(math.exp(-0.0034 * phytateMg + 0.0065 * vitCMg), 0.2, 4.0)
end
function O.fatFactor(lipidsG)
    return K.clamp(1 - math.exp(-lipidsG / 3), 0.05, 1.0)
end
return O
"""


def rows():
    return {k: v for k, v in dials.values().items() if k.split(".")[0] in DOMAINS}


def raw_rows():
    return dials.load_rows(dials._read(dials._path(dials.REPO, dials.REGISTRY_REL)))


def runtime(edits=()):
    """A fresh runtime with NR_Core, the registry (each (old, new) edit applied to its text first) and the kernels."""
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    load = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    for path in [CORE, DIALS] + kernel_files():
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        if path == DIALS:
            for old, new in edits:
                assert src.count(old) == 1, old
                src = src.replace(old, new)
        load(src, "@" + os.path.basename(path))()
    return rt, rt.globals().NutritionRevamp.kernel


def field(K, dial_id):
    v = K
    for seg in dial_id.split("."):
        v = v[int(seg)] if seg.isdigit() else v[seg]
    return v


def dump(rt, t):
    """A Lua table as nested (key, value) pairs in its pairs order, numbers as their exact hex."""
    keys = rt.eval("function(t) local ks = {} for k in pairs(t) do ks[#ks + 1] = k end return ks end")(t)
    out = []
    for i in range(1, len(keys) + 1):
        k = keys[i]
        v = t[k]
        out.append((k, dump(rt, v) if lua51.lua_type(v) == "table" else float(v).hex()))
    return out


def test_the_wave_holds_its_dials():
    got = rows()
    assert sum(1 for k in got if k.startswith("stomach.")) == 37
    assert sum(1 for k in got if k.startswith("satiety.")) == 31
    assert "stomach.BIOAVAIL.phytate" not in got                     # absorb zeroes phytate itself: no row needed


def test_each_kernel_field_holds_its_registry_value():
    _, K = runtime()
    for dial_id, value in rows().items():
        assert field(K, dial_id) == value, dial_id


def test_the_moved_values_and_the_pairs_order_are_the_code_they_replaced():
    rt, K = runtime()
    old = rt.execute(OLD)
    for dom in DOMAINS:
        for name in old[dom].keys():
            got, want = K[dom][name], old[dom][name]
            if lua51.lua_type(want) == "table":
                assert dump(rt, got) == dump(rt, want), name
            else:
                assert float(got).hex() == float(want).hex(), name
    assert K.satiety.SLEEP_DEBT_FULL_H == 2.0                         # derived: SLEEP_NEED_H 7.5 - SLEEP_SHORT_H 5.5
    for p in (0, 1, 37.5, 250, 400, 886, 2000):
        for c in (0, 1, 12.5, 100, 213, 1000):
            assert float(K.stomach.ironFactor(p, c)).hex() == float(old.ironFactor(p, c)).hex(), (p, c)
    for g in (0, 1e-9, 0.01, 0.154, 1, 3, 10, 28, 30, 1000):
        assert float(K.stomach.fatFactor(g)).hex() == float(old.fatFactor(g)).hex(), g


def test_meal_req_is_the_fed_threshold_and_the_vanilla_rows_are_fixed():
    raw = raw_rows()
    assert raw["satiety.MEAL_REQ"]["same"] == "hungerCurve.FED_M" and "value" not in raw["satiety.MEAL_REQ"]
    assert dials.linked("satiety.MEAL_REQ") == ["hungerCurve.FED_M", "satiety.MEAL_REQ"]
    _, K = runtime()
    assert K.satiety.MEAL_REQ == K.hungerCurve.FED_M == 3.80654
    for dial_id in JOINT_FIT:
        assert raw[dial_id]["fit"] == "fit-11g-20261012d", dial_id   # the joint fit owns the eight (FED_M for MEAL_REQ)
    for dial_id, src in FIXED.items():
        assert raw[dial_id].get("fixed") is True and raw[dial_id]["src"] == src, dial_id
    text = dials._read(dials._path(dials.REPO, dials.REGISTRY_REL))
    for dial_id in ("satiety.MEAL_REQ", "satiety.HEARTY", "satiety.NIC_WITHDRAWAL_MAX", "satiety.DISCOMFORT_MAX"):
        with pytest.raises(ValueError):
            dials.set_value(text, dial_id, "1.2")


def test_the_wave_orderings_and_divisor_floors_hold():
    _, K = runtime()
    raw = raw_rows()
    assert raw["stomach.CAPACITY_MAX_G"]["max"] < raw["stomach.CAPACITY_HARD_G"]["min"]   # a divisor (hard - max)
    assert raw["stomach.IRON_MIN"]["max"] <= 1 <= raw["stomach.IRON_MAX"]["min"]          # the band holds no meal at 1
    assert raw["stomach.IRON_PHYTATE_SLOPE"]["max"] <= 0 <= raw["stomach.IRON_VITC_SLOPE"]["min"]
    assert raw["satiety.SLEEP_SHORT_H"]["max"] < raw["acute.SLEEP_NEED_H"]["min"]          # the full debt stays positive
    for dial_id in DIVISORS:
        assert raw[dial_id]["min"] > 0, dial_id
    assert raw["satiety.FULL_WEIGHT"]["max"] <= 1 and raw["satiety.LIQUID_WEIGHT"]["max"] <= 1   # fit_gut_satiety's bounds


def test_a_registry_fed_threshold_moves_the_meal_read_through_same_and_a_registry_capacity_moves_the_fill():
    _, K = runtime([("D['hungerCurve.FED_M'] = { value = 3.80654,", "D['hungerCurve.FED_M'] = { value = 6,"),
                    ("D['stomach.CAPACITY_MAX_G'] = { value = 730,", "D['stomach.CAPACITY_MAX_G'] = { value = 800,")])
    assert K.satiety.MEAL_REQ == 6 and K.hungerCurve.FED_M == 6
    assert K.satiety.mealRead(6) == pytest.approx(0.75)               # 1 - 1 / (1 + 3): the request read at MEAL_REQ
    st = K.stomach.new()
    st.liquid = 400
    assert K.stomach.fill(st) == 400 / 800


def test_a_registry_short_night_moves_the_full_debt_and_a_registry_slope_moves_the_iron_factor():
    _, K = runtime([("D['satiety.SLEEP_SHORT_H'] = { value = 5.5,", "D['satiety.SLEEP_SHORT_H'] = { value = 6.5,"),
                    ("D['stomach.IRON_PHYTATE_SLOPE'] = { value = -0.0034,",
                     "D['stomach.IRON_PHYTATE_SLOPE'] = { value = -0.0068,"),
                    ("D['stomach.FAT_FLOOR'] = { value = 0.05,", "D['stomach.FAT_FLOOR'] = { value = 0.1,")])
    assert K.satiety.SLEEP_DEBT_FULL_H == 1.0
    assert K.satiety.sleepFactor(1.0) == pytest.approx(1.18)
    assert K.stomach.ironFactor(100, 0) == pytest.approx(math.exp(-0.68))
    assert K.stomach.fatFactor(0) == 0.1


def test_the_meal_seed_cap_stays_on_the_fitted_weights():
    # Plan 19 Task 3d fix 1 (M2): MEAL_SEED_MAX is the weigh of a 1000 kcal meal of 150 g protein, 500 g carbohydrate and
    # 350 g fat ... a refit of W_PROTEIN or W_FAT that leaves the cap's meaning stale fails here
    _, K = runtime()
    v = K.vector.new()
    v.calories = 1000
    v.proteins = 150 / 4
    v.carbs = 500 / 4
    v.lipids = 350 / 9
    assert abs(K.satiety.MEAL_SEED_MAX / K.satiety.weigh(v) - 1) < 0.01


def test_replay_live_set_constants_treats_a_same_group_as_one_dial():
    # Plan 19 Task 3d fix 1 (M4): a snapshot or bundle that sets satiety.MEAL_REQ alone moves hungerCurve.FED_M with it
    import replay_live
    _, K = runtime()
    replay_live.set_constants(K, {"satiety.MEAL_REQ": 6})
    assert (K.satiety.MEAL_REQ, K.hungerCurve.FED_M) == (6, 6)
