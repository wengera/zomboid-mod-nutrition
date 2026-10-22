"""Plan 19 Task 3c (wave W6): the fluids and energy dials resolve from NR_Data_Dials.lua.

Each kernel field holds its registry row's value, and every moved value, every table's `pairs` order and the derived
WATER_PER_MMOL read exactly as the code they replaced. The engine class values (energy.CLASS_MET) are fixed vanilla
rows, and the copies of them are `same` links: the training METs, the bills of the classes with no Compendium row and
the band MET of caloriesModifier 3. The other duplicates the wave unified are `same` links too: the Parched thirst knot
(hybrid.THIRST_4), the idle bill (standing quietly) and the two bands that bill a Compendium code of their own. A registry-only edit, made before the kernels load with no code
change, moves a kernel output (the mutation probes, dial-inventory section 3.4).
"""
import os
import sys

import lupa.lua51 as lua51
import pytest

from .conftest import CORE, DIALS, REPO, kernel_files

sys.path.insert(0, os.path.join(REPO, "tools"))
import dials  # noqa: E402

DOMAINS = ("fluids", "energy")
DIVISORS = ("fluids.ALC_KNEE_PCT", "fluids.NA_TAU_H", "fluids.K_TAU_H", "fluids.OSM_SLOPE", "fluids.EMA_MIN",
            "fluids.THIRST_KNOTS.2.1", "fluids.NA_SWEAT_DEF_FULL", "fluids.OSM_REF", "energy.AT_FULL_DEP", "energy.AT_TAU_ON", "energy.AT_TAU_OFF",
            "energy.EPOC_TAU_H")
# the training METs and the other copies of an engine class value, each with the class it resolves to
CLASS_LINKS = {
    "training.MET_FLOOR": "Default", "training.BAND1_MET": "Fitness", "training.BAND2_MET": "FitnessHeavy",
    "training.CLIMB_MET.JumpFence": "JumpFence", "training.CLIMB_MET.ClimbRope": "ClimbRope",
    "energy.BAND_MET.3": "Fitness",
    "energy.COMPENDIUM.DrivingCar": "DrivingCar", "energy.COMPENDIUM.LightDomestic": "LightDomestic",
    "energy.COMPENDIUM.HeavyDomestic": "HeavyDomestic", "energy.COMPENDIUM.DefaultExercise": "DefaultExercise",
    "energy.COMPENDIUM.Walking2kmh": "Walking2kmh", "energy.COMPENDIUM.JumpFence": "JumpFence",
    "energy.COMPENDIUM.Fitness": "Fitness", "energy.COMPENDIUM.FitnessHeavy": "FitnessHeavy",
}
OTHER_LINKS = {
    "fluids.THIRST_KNOTS.5.2": "hybrid.THIRST_4",
    "energy.BAND_MET.0_5": "energy.COMPENDIUM.SeatedResting",
    "energy.BAND_MET.2": "energy.COMPENDIUM.UsingTools",
    "energy.COMPENDIUM.Default": "energy.COMPENDIUM.StandingAtRest",
}

# The replaced constructors, verbatim from c10cfc8e (the values and the assignment order the pairs order follows).
OLD = """
local O = { fluids = {}, energy = {} }
O.fluids.TBW_PER_LM = 0.73
O.fluids.OSM_REF = 140
O.fluids.BASAL_G = 2000
O.fluids.BASAL_G_PER_LM = 32
O.fluids.HIGH_THIRST = 1.5
O.fluids.LOW_THIRST = 0.5
O.fluids.SWEAT_LH = 1.0
O.fluids.SWEAT_MET_LO = 3
O.fluids.SWEAT_MET_HI = 8
O.fluids.SWEAT_CAP = 1.5
O.fluids.SWEATK_RANGE = { 0.5, 1.5 }
O.fluids.NA_SWEAT_MEAN = 37
O.fluids.NA_SWEAT_RANGE = { 10, 90 }
O.fluids.K_SWEAT = 5
O.fluids.COLD_DIURESIS_LH = 0.1
O.fluids.ALC_DIURESIS_G_PER_G = 4
O.fluids.ALC_HYPO_K = 0.45
O.fluids.ALC_KNEE_PCT = 2
O.fluids.CLEAR_GH = 672
O.fluids.NA_TAU_H = 33.8
O.fluids.K_TAU_H = 24
O.fluids.THIRST_KNOTS = { { 0, 0 }, { 1, 0.12 }, { 2, 0.25 }, { 3, 0.45 }, { 4, 0.84 }, { 8, 1.0 } }
O.fluids.OSM_SLOPE = 0.03
O.fluids.OSM_GAIN = 0.25
O.fluids.OSM_MAX = 4
O.fluids.HYPO_NA = 135
O.fluids.HYPO_CAP = 0.09
O.fluids.HYPONAT = { 135, 120, 112 }
O.fluids.SWEAT_ACTIVE_SHARE = 0.5
O.fluids.BASAL_NA = 8
O.fluids.EMA_MIN = 360
O.fluids.WATER_PER_MMOL = 1000 / 140
O.fluids.ECF_PER_KG = 0.20
O.fluids.DEFEND_ONSET = 0.08
O.fluids.DEFEND_FULL = 0.20
O.fluids.NA_SWEAT_MIN_FRAC = 0.325
O.fluids.NA_SWEAT_DEF_FULL = 331
O.fluids.NA_SWEAT_ABS_MIN = 10
O.energy.REE_A = 19.7
O.energy.REE_B = 413
O.energy.AT_MAX = 0.10
O.energy.AT_FULL_DEP = 0.5
O.energy.AT_TAU_ON = 7
O.energy.AT_TAU_OFF = 14
O.energy.COLD_MAX = 4.9
O.energy.MET_REST = 1.0
O.energy.CLASS_MET = {}
O.energy.CLASS_MET.Sleeping = 0.8
O.energy.CLASS_MET.SeatedResting = 1.0
O.energy.CLASS_MET.StandingAtRest = 1.1
O.energy.CLASS_MET.SedentaryActivity = 1.2
O.energy.CLASS_MET.DrivingCar = 1.4
O.energy.CLASS_MET.Default = 1.5
O.energy.CLASS_MET.LightDomestic = 1.6
O.energy.CLASS_MET.Walking2kmh = 1.9
O.energy.CLASS_MET.HeavyDomestic = 2.0
O.energy.CLASS_MET.UsingTools = 2.5
O.energy.CLASS_MET.DefaultExercise = 3.0
O.energy.CLASS_MET.Walking5kmh = 3.1
O.energy.CLASS_MET.LightWork = 3.2
O.energy.CLASS_MET.MediumWork = 3.9
O.energy.CLASS_MET.JumpFence = 4.0
O.energy.CLASS_MET.DiggingSpade = 5.5
O.energy.CLASS_MET.HeavyWork = 6.0
O.energy.CLASS_MET.Fitness = 6.0
O.energy.CLASS_MET.Running10kmh = 6.9
O.energy.CLASS_MET.ClimbRope = 8.0
O.energy.CLASS_MET.ForestryAxe = 8.0
O.energy.CLASS_MET.FitnessHeavy = 9.0
O.energy.CLASS_MET.Running15kmh = 9.5
O.energy.CLASS_MET.MAX = 10.3
O.energy.COMPENDIUM = {}
O.energy.COMPENDIUM.Sleeping = 1.0
O.energy.COMPENDIUM.SeatedResting = 1.0
O.energy.COMPENDIUM.StandingAtRest = 1.3
O.energy.COMPENDIUM.SedentaryActivity = 1.5
O.energy.COMPENDIUM.DrivingCar = 1.4
O.energy.COMPENDIUM.Default = 1.3
O.energy.COMPENDIUM.LightDomestic = 1.6
O.energy.COMPENDIUM.HeavyDomestic = 2.0
O.energy.COMPENDIUM.UsingTools = 2.5
O.energy.COMPENDIUM.DefaultExercise = 3.0
O.energy.COMPENDIUM.Walking2kmh = 1.9
O.energy.COMPENDIUM.Walking5kmh = 3.8
O.energy.COMPENDIUM.LightWork = 3.0
O.energy.COMPENDIUM.MediumWork = 4.0
O.energy.COMPENDIUM.HeavyWork = 6.0
O.energy.COMPENDIUM.JumpFence = 4.0
O.energy.COMPENDIUM.DiggingSpade = 5.0
O.energy.COMPENDIUM.Fitness = 6.0
O.energy.COMPENDIUM.FitnessHeavy = 9.0
O.energy.COMPENDIUM.Running10kmh = 9.3
O.energy.COMPENDIUM.ClimbRope = 8.0
O.energy.COMPENDIUM.ForestryAxe = 6.5
O.energy.COMPENDIUM.Running15kmh = 14.8
O.energy.COMPENDIUM.MAX = 14.8
O.energy.BAND_MET = {}
O.energy.BAND_MET[0.5] = 1.0
O.energy.BAND_MET[2] = 2.5
O.energy.BAND_MET[3] = 6.0
O.energy.BAND_MET[4] = 4.3
O.energy.BAND_MET[5] = 5.5
O.energy.BAND_MET[8] = 7.0
O.energy.EXERCISE_MET = {}
O.energy.EXERCISE_MET.squats = 3.0
O.energy.EXERCISE_MET.pushups = 3.8
O.energy.EXERCISE_MET.situp = 3.8
O.energy.EXERCISE_MET.burpees = 7.5
O.energy.EXERCISE_MET.barbellcurl = 3.5
O.energy.EXERCISE_MET.dumbbellpress = 3.5
O.energy.EXERCISE_MET.bicepscurl = 3.5
O.energy.LOAD_FLOOR = { { 2.3, 4.0 }, { 6.8, 4.5 }, { 22.7, 6.5 } }
O.energy.FALL_EPS = 1e-4
O.energy.EPOC_F = 0.10
O.energy.EPOC_TAU_H = 0.5
O.energy.EPOC_FLOOR_KCAL = 1e-6
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
    """K.<dial_id> by its path, a numeric segment indexing an array and 0_5 the key 0.5."""
    v = K
    for seg in dial_id.split("."):
        if seg == "0_5":
            v = v[0.5]
        else:
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
    assert sum(1 for k in got if k.startswith("fluids.")) == 49
    assert sum(1 for k in got if k.startswith("energy.")) == 79


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
    assert K.fluids.WATER_PER_MMOL == 1000 / 140                       # derived from OSM_REF, the same double
    assert K.energy.activityMet("NoSuchClass", False, 1, 0, None) == 1.3   # the fallback reads COMPENDIUM.Default
    assert K.energy.exerciseMet(None) == (6.0, False)


def test_the_engine_class_values_are_fixed_and_their_copies_resolve_to_them():
    raw = raw_rows()
    names = [n for n in raw if n.startswith("energy.CLASS_MET.")]
    assert len(names) == 24
    for n in names:
        assert raw[n].get("fixed") is True and raw[n]["src"] == "vanilla #2632", n
    _, K = runtime()
    for dial_id, cls in CLASS_LINKS.items():
        assert raw[dial_id]["same"] == "energy.CLASS_MET." + cls and "value" not in raw[dial_id], dial_id
        assert dials.values()[dial_id] == K.energy.CLASS_MET[cls], dial_id
    for dial_id, target in OTHER_LINKS.items():
        assert raw[dial_id]["same"] == target and "value" not in raw[dial_id], dial_id
    for dial_id in ("fluids.THIRST_KNOTS.2.2", "fluids.THIRST_KNOTS.3.2"):
        assert raw[dial_id].get("fixed") is True, dial_id                # vanilla THIRST levels 1 and 2 (#0509)
    text = dials._read(dials._path(dials.REPO, dials.REGISTRY_REL))
    with pytest.raises(ValueError):
        dials.set_value(text, "energy.CLASS_MET.Fitness", "6.5")
    with pytest.raises(ValueError):
        dials.set_value(text, "training.BAND1_MET", "6.5")


def test_the_wave_orderings_and_divisor_floors_hold():
    _, K = runtime()
    F, E = K.fluids, K.energy
    raw = raw_rows()
    assert raw["fluids.SWEAT_MET_LO"]["max"] < raw["fluids.SWEAT_MET_HI"]["min"]           # a divisor (HI - LO)
    assert raw["fluids.DEFEND_ONSET"]["max"] < raw["fluids.DEFEND_FULL"]["min"]           # a divisor (b - a)
    assert raw["fluids.HYPO_CAP"]["max"] < 0.1                                             # under the autoDrink trigger
    for dial_id in DIVISORS:
        assert raw[dial_id]["min"] > 0, dial_id
    assert F.SWEATK_RANGE[1] < F.SWEATK_RANGE[2]
    assert F.NA_SWEAT_RANGE[1] < F.NA_SWEAT_MEAN < F.NA_SWEAT_RANGE[2]
    knots = [(F.THIRST_KNOTS[i][1], F.THIRST_KNOTS[i][2]) for i in range(1, 7)]
    assert all(a[0] < b[0] for a, b in zip(knots, knots[1:]))                             # K.interp needs ascending x
    assert all(a[1] <= b[1] for a, b in zip(knots, knots[1:]))
    assert knots[4][1] == K.hybrid.THIRST_4
    assert F.HYPONAT[1] > F.HYPONAT[2] > F.HYPONAT[3]
    assert F.HYPONAT[1] < F.OSM_REF and F.HYPO_NA < F.OSM_REF
    assert F.NA_SWEAT_ABS_MIN <= F.NA_SWEAT_RANGE[1]  # a floor above a low draw would lift its no-deficit baseline
    cls = [E.CLASS_MET[E.CLASS_LIST[i]] for i in range(1, len(E.CLASS_LIST) + 1)]
    assert all(a <= b for a, b in zip(cls, cls[1:]))                                       # classOf's bucketing order
    floors = [E.LOAD_FLOOR[i][1] for i in range(1, 4)]
    assert floors == sorted(floors) and len(set(floors)) == 3                             # loadFloor: ascending


def test_a_registry_knot_moves_the_volume_thirst_and_a_registry_reference_moves_the_water_per_mmol():
    _, K = runtime([("D['fluids.THIRST_KNOTS.4.2'] = { value = 0.45,", "D['fluids.THIRST_KNOTS.4.2'] = { value = 0.5,"),
                    ("D['fluids.OSM_REF'] = { value = 140,", "D['fluids.OSM_REF'] = { value = 145,")])
    assert K.fluids.tVol(3) == 0.5
    assert K.fluids.WATER_PER_MMOL == 1000 / 145


def test_a_registry_edge_moves_the_hyponatraemia_grade_and_a_registry_threshold_moves_the_hypotonic_cap():
    _, K = runtime([("D['fluids.HYPONAT.1'] = { value = 135,", "D['fluids.HYPONAT.1'] = { value = 130,")])
    assert K.fluids.hyponatGrade(132) == 0 and K.fluids.HYPO_NA == 135
    _, K = runtime([("D['fluids.HYPO_NA'] = { value = 135,", "D['fluids.HYPO_NA'] = { value = 130,")])
    assert K.fluids.thirstTarget(3, 1, 132, 0) > K.fluids.HYPO_CAP and K.fluids.HYPONAT[1] == 135


def test_a_registry_standing_bill_moves_the_idle_and_unknown_class_bills_through_same():
    _, K = runtime([("D['energy.COMPENDIUM.StandingAtRest'] = { value = 1.3,",
                     "D['energy.COMPENDIUM.StandingAtRest'] = { value = 1.4,")])
    assert K.energy.COMPENDIUM.Default == 1.4
    assert K.energy.activityMet("NoSuchClass", False, 1, 0, None) == 1.4


def test_a_registry_class_value_moves_every_copy_through_same_and_a_registry_ree_moves_the_bill():
    edit = ("D['energy.CLASS_MET.Fitness'] = { value = 6.0, unit = 'MET', min = 6.0, max = 6.0,",
            "D['energy.CLASS_MET.Fitness'] = { value = 6.5, unit = 'MET', min = 6.5, max = 6.5,")
    _, K = runtime([edit, ("D['energy.REE_A'] = { value = 19.7,", "D['energy.REE_A'] = { value = 20.7,")])
    assert (K.training.BAND1_MET, K.energy.BAND_MET[3], K.energy.COMPENDIUM.Fitness) == (6.5, 6.5, 6.5)
    assert K.energy.exerciseMet(None) == (6.5, False)
    assert K.energy.ree(50) == 20.7 * 50 + 413
