"""Plan 19 Task 3e (wave W8): the acute, effects and adapter dials (eff, nut, met, writer) resolve from NR_Data_Dials.lua.

Each kernel field holds its registry row's value, each adapter field reads its row at load, and every moved value, every
table's `pairs` order and the two stimulant sets read exactly as the code they replaced. The wave's duplicates are `same`
links: the protein-energy grade's S0115 cut-offs are the refeeding risk's (acute.RISK_*), its RDA is the aerobic
protein gate's (aerobic.P_LOW), the S0691 energy-availability threshold is the aerobic gain gate's (EA_FULL and
EA_EDGES[1]), the cold hour's coldMult is the shiver dead band (acute.COLD_ON), and the accrual trait multipliers are the
sleep-need pair (nut.NEED_*); the effects' regeneration tiers read the drain kernel's. A registry-only edit, made before
the kernels load with no code change, moves a kernel output (the mutation probes, dial-inventory section 3.4), and
replay_live.set_constants writes a same group's array elements by the ids' path grammar.
"""
import os
import re
import sys

import lupa.lua51 as lua51
import pytest

from .conftest import CORE, DIALS, REPO, kernel_files

LUA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua")
sys.path.insert(0, os.path.join(REPO, "tools"))
import dials  # noqa: E402

KERNEL_DOMAINS = ("acute", "effects")
ADAPTERS = {"eff": ("effects", "EFF", "NR_Server_Effects.lua"), "nut": ("nutrients", "NUT", "NR_Server_Nutrients.lua"),
            "met": ("metabolism", "MET", "NR_Server_Metabolism.lua"), "writer": ("writer", "W", "NR_Server_Writer.lua")}
LINKS = {
    "effects.PE_BMI_OK": "acute.RISK_BMI_MOD", "effects.PE_BMI_LOW": "acute.RISK_BMI_HIGH",
    "effects.PE_STARVED_3": "acute.RISK_DAYS_MOD", "effects.PE_STARVED_4": "acute.RISK_DAYS_HIGH",
    "effects.PE_PROT_OK": "aerobic.P_LOW",
    "effects.EA_FULL": "aerobic.EA_THRESHOLD", "effects.EA_EDGES.1": "aerobic.EA_THRESHOLD",
    "acute.COLD_ON": "acute.SHIVER_DEADBAND",
    "effects.BG_EDGES.2": "acute.IU_BG_HI", "effects.BG_EDGES.3": "acute.IU_BG_LO",
    "eff.TRAIT_NEEDS_LESS_ACC": "nut.NEED_LESS", "eff.TRAIT_NEEDS_MORE_ACC": "nut.NEED_MORE",
}
FIXED = {"effects.INTOX_MAX": "vanilla #2371", "nut.LITRES_PER_THIRST": "vanilla #2928 #2939"}
DIVISORS = ("acute.CAF_THALF_H", "acute.CAF_THALF_SLOW_H", "acute.CAF_MEAN_H", "acute.CAF_TOL_REF", "acute.CAF_TOL_TAU_H",
            "acute.GUT_T_HALF", "acute.WIDMARK_R.1", "acute.WIDMARK_R.2", "acute.HANG_PEAK",
            "acute.STIM_REALISTIC.INTOX_FULL_BAC", "acute.STIM_GAME_OVERRIDES.INTOX_FULL_BAC", "acute.IU_ALC_KNOTS.2.1",
            "acute.GLYC_REF", "acute.GLYC_SPAN", "acute.GLYC_TAU_H", "acute.USE_MET_SPAN", "acute.BG_TAU_CHO_H",
            "acute.BG_TAU_H", "acute.CHI_W", "acute.CHI_S", "acute.WINDOW_H", "acute.IU_SLEEP_SPAN_H",
            "acute.IU_SLEEP_DEBT_H", "acute.EX_TAU_H", "acute.COLD_TAU_H", "acute.RET_TAU_D", "acute.CREDIT_MG",
            "acute.CREDIT_BASE_MG", "effects.CAF_STEP", "effects.IUS_STEP", "effects.IU_STEP", "effects.EX_STEP",
            "effects.CAF_EC50", "nut.ALC_EMA_DAYS")
# (lower, upper): the lower dial's max under the upper's min, so the difference a kernel divides by stays positive
DISJOINT = (("acute.CAF_WD_ONSET_H", "acute.CAF_WD_PEAK_H"), ("acute.CAF_WD_PEAK_H", "acute.CAF_WD_END_H"),
            ("acute.SHIVER_DEADBAND", "acute.SHIVER_FULL"), ("acute.IU_BG_LO", "acute.IU_BG_HI"),
            ("acute.IU_ALC_KNOTS.2.1", "acute.IU_ALC_KNOTS.3.1"), ("acute.IU_ALC_KNOTS.3.1", "acute.IU_ALC_KNOTS.4.1"),
            ("effects.CAF_SLEEP_ZERO", "effects.CAF_SLEEP_FULL"), ("effects.EA_LOW", "effects.EA_MID"),
            ("effects.EA_MID", "aerobic.EA_THRESHOLD"), ("acute.IU_BG_HI", "effects.BG_EDGES.1"), ("satiety.SLEEP_SHORT_H", "acute.SLEEP_NEED_H"))

# The replaced constructors, verbatim from 1e4bc8fc (the values and the assignment order the pairs order follows).
OLD = """
local O = { acute = {}, effects = {} }
O.acute.CAF_ABSORB = 1.0
O.acute.CAF_THALF_H = 5.0
O.acute.CAF_THALF_SLOW_H = 9.7
O.acute.CAF_SLOW_SHARE = 0.5
O.acute.CAF_MEAN_H = 168
O.acute.CAF_TOL_REF = 400
O.acute.CAF_TOL_TAU_H = 168
O.acute.CAF_WD_TOL = 0.25
O.acute.CAF_WD_LOW_MG = 10.7
O.acute.CAF_WD_ONSET_H = 12
O.acute.CAF_WD_PEAK_H = 36
O.acute.CAF_WD_END_H = 120
O.acute.CAF_EFFECT_MGKG = 3
O.acute.GUT_T_HALF = 0.5
O.acute.WIDMARK_R = { 0.68, 0.55 }
O.acute.BETA = 0.015
O.acute.HANG_PEAK = 0.05
O.acute.STIM_REALISTIC = { MODE = 2, CAF_OFF_MAX = 0.35, INTOX_FULL_BAC = 0.20, HANG_H = 6 }
O.acute.STIM_GAME_OVERRIDES = { MODE = 1, CAF_OFF_MAX = 0.12, INTOX_FULL_BAC = 0.31, HANG_H = 3 }
O.acute.IU_ALC_KNOTS = { { 0, 0 }, { 0.03, 0.30 }, { 0.05, 1.00 }, { 0.08, 1.60 } }
O.acute.IU_ALC_CAP = 2.0
O.acute.GLYC_REF = 462
O.acute.GLYC_HIGH = 102
O.acute.GLYC_LOW = 253
O.acute.GLYC_PIVOT = 3
O.acute.GLYC_SPAN = 3
O.acute.GLYC_TAU_H = 24
O.acute.GLYC_MAX = 600
O.acute.USE_WORK = 51.5
O.acute.USE_MET_LO = 3
O.acute.USE_MET_SPAN = 4.5
O.acute.USE_MAX = 1.6
O.acute.USE_SHIVER = 52
O.acute.SHIVER_FULL = 3.5
O.acute.SHIVER_DEADBAND = 1.05
O.acute.BG_NORMAL = 5.0
O.acute.BG_EXERTION = 2.5
O.acute.BG_EX_G = 0.2
O.acute.BG_EX_MET = 6
O.acute.BG_ALC_FAST = 3.0
O.acute.BG_ALC_FAST_H = 12
O.acute.BG_TAU_CHO_H = 0.25
O.acute.BG_TAU_H = 1
O.acute.BG_MIN = 2.0
O.acute.BG_MAX = 8.0
O.acute.IU_BG_HI = 3.0
O.acute.IU_BG_LO = 2.6
O.acute.IU_BG_MAX = 0.90
O.acute.SLEEP_NEED_H = 7.5
O.acute.CHI_W = 18.2
O.acute.CHI_S = 4.2
O.acute.CHI_W_DEBT = 0.02
O.acute.CHI_W_DEBT_MAX = 20
O.acute.S_FLOOR_DEBT = 0.01
O.acute.S_FLOOR_MAX = 0.25
O.acute.S_RESTED = 0.17
O.acute.NAP_MIN_H = 1
O.acute.BOUT_GAP_H = 10 / 60
O.acute.WINDOW_H = 24
O.acute.DEBT_MAX = 40
O.acute.REPAY = 0.5
O.acute.CIRC_AMP = 0.12
O.acute.CIRC_PEAK_H = 4
O.acute.IU_SLEEP_ZERO_H = 16
O.acute.IU_SLEEP_SPAN_H = 8
O.acute.IU_SLEEP_DEBT_H = 10.5
O.acute.IU_SLEEP_MAX = 1.5
O.acute.VIG_WINDOW_H = 1
O.acute.EX_TAU_H = 6
O.acute.COLD_ON = 1.05
O.acute.COLD_TAU_H = 6
O.acute.RET_TAU_D = 14
O.acute.IU_DEHYD_FROM = 1
O.acute.IU_DEHYD_KNEE = 2
O.acute.IU_DEHYD_SLOPE1 = 0.45
O.acute.IU_DEHYD_SLOPE2 = 0.22
O.acute.IU_DEHYD_MAX = 0.89
O.acute.IU_IRON = { 0, 0, 0.38, 0.76 }
O.acute.CREDIT_BASE = 0.50
O.acute.CREDIT_GAIN = 0.60
O.acute.CREDIT_MG = 200
O.acute.CREDIT_BASE_MG = 100
O.acute.IU_MAX = 2.5
O.acute.LOW_KCAL_KG = 5
O.acute.MASS_WINDOW_H = 2160
O.acute.REFEED_DAYS = 7
O.acute.RESTART_KCAL_KG = 10
O.acute.RESTART_LOW_KCAL_KG = 5
O.acute.RESTART_LOW_BMI = 14
O.acute.REFEED_P = 0.23
O.effects.CAF_STEP = 50
O.effects.CAF_BANDS = 16
O.effects.WD_BANDS = 4
O.effects.ALC_EDGES = { 0.0735, 0.125 }
O.effects.BG_EDGES = { 3.5, 3.0, 2.6 }
O.effects.IUS_STEP = 0.125
O.effects.IUS_BANDS = 12
O.effects.DEBT_EDGES = { 4, 8 }
O.effects.IU_STEP = 0.1
O.effects.IU_BANDS = 25
O.effects.DEHYD_EDGES = { 1, 1.5, 2, 2.5, 3, 4, 6, 10 }
O.effects.EX_STEP = 7.5
O.effects.EX_BANDS = 4
O.effects.EA_EDGES = { 30, 20, 10 }
O.effects.EA_FULL = 30
O.effects.EA_MID = 15
O.effects.EA_MID_M = 1.25
O.effects.EA_LOW = 5
O.effects.EA_LOW_M = 1.40
O.effects.PE_BMI_OK = 18.5
O.effects.PE_BMI_THIN = 17
O.effects.PE_BMI_LOW = 16
O.effects.PE_STARVED_3 = 5
O.effects.PE_STARVED_4 = 10
O.effects.PE_PROT_OK = 0.8
O.effects.PE_PROT_2 = 0.6
O.effects.PE_PROT_3 = 0.4
O.effects.AIM_K = 0.25
O.effects.AIM_LO = 0.90
O.effects.AIM_HI = 1.60
O.effects.DEBT_K = 0.005
O.effects.DEBT_F_MAX = 0.10
O.effects.CAF_EC50 = 150
O.effects.CAF_TOL_BLUNT = 0.6
O.effects.CAF_SLEEP_FULL = 107
O.effects.CAF_SLEEP_ZERO = 32.1
O.effects.END_FLOOR = 0.3
O.effects.REST_DIV = 1.5
O.effects.M_LO = 0.2
O.effects.M_HI = 5.0
O.effects.R_LO = 0.25
O.effects.R_HI = 2.0
O.effects.NV_GRANT = 14
O.effects.NV_SLOW = 0.5
O.effects.NV_REGRANT = 3
O.effects.NV_ZINC = 3
O.effects.INTOX_MAX = 100
O.effects.CREDIT_E24 = 200
O.effects.CREDIT_B1 = 60
O.effects.CREDIT_COLD_H = 0.25
O.acute.STIM = { {}, O.acute.STIM_REALISTIC }
for name, v in pairs(O.acute.STIM_REALISTIC) do
    O.acute.STIM[1][name] = v
end
for name, v in pairs(O.acute.STIM_GAME_OVERRIDES) do
    O.acute.STIM[1][name] = v
end
return O
"""
# The adapters' replaced literals, from 1e4bc8fc.
OLD_ADAPTERS = {
    "effects": {"REGEN_STANDARD": 0.002, "REGEN_REDUCED": 0.0013, "REGEN_SEVERE": 0.0008, "REGEN_SLEEPING": 0.02,
                "REGEN_FOOD": 0.0087, "SOL_CAF_H": 0.15, "SOL_VIG_H": 0.15, "SOL_ALC_MUL": 0.6,
                "TRAIT_NEEDS_LESS_ACC": 0.7, "TRAIT_NEEDS_MORE_ACC": 1.3, "MET_EXERT": 3},
    "nutrients": {"FED_FILL": 0.05, "ALC_HISTORY_GKG": 0.5, "ALC_EMA_DAYS": 7, "MG_DEPLETED_GRADE": 3,
                  "LITRES_PER_THIRST": 2},
    "metabolism": {"BALANCE_BONUS": 1.05},
    "writer": {"SIP_EPS": 1e-6, "UNHAPPY_HI": 59, "SEED_PLATE_MAX": 667},
}


def text():
    return dials._read(dials._path(dials.REPO, dials.REGISTRY_REL))


def raw_rows():
    return dials.load_rows(text())


def rows(domains):
    return {k: v for k, v in dials.values().items() if k.split(".")[0] in domains}


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


def value_edit(dial_id, new):
    """The (old, new) registry edit that sets dial_id's value to the text new (and its range to it, for a fixed row)."""
    line = dials.source_line(dial_id)
    head = "D['%s'] = { value = %s," % (dial_id, dials.value_text(line))
    assert line.startswith(head), line
    return head, "D['%s'] = { value = %s," % (dial_id, new)


def field(K, dial_id):
    """K.<dial_id> by its path, a numeric segment indexing an array."""
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


@pytest.fixture(scope="module")
def server():
    from .server_host import Host
    return Host()


def test_the_wave_holds_its_dials():
    got = raw_rows()
    count = {d: sum(1 for k in got if k.startswith(d + ".")) for d in ("acute", "effects", "eff", "nut", "met", "writer")}
    # acute: 100 rows of this wave and the six S0115 risk cut-offs W4 moved ahead; nut: five and W5's sleep-need pair
    assert count == {"acute": 106, "effects": 61, "eff": 7, "nut": 7, "met": 1, "writer": 3}


def test_each_kernel_field_holds_its_registry_value():
    _, K = runtime()
    for dial_id, value in rows(KERNEL_DOMAINS).items():
        assert field(K, dial_id) == value, dial_id


def test_each_adapter_field_reads_its_row_at_load(server):
    for dial_id, value in rows(tuple(ADAPTERS)).items():
        dom, _, name = dial_id.partition(".")
        table, alias, fname = ADAPTERS[dom]
        assert server.NR.server[table][name] == value, dial_id
        with open(os.path.join(LUA, "server", fname), encoding="utf-8") as fh:
            src = fh.read()
        assert re.search(r'^%s\.%s = K\.dials\.get\("%s"\)$' % (alias, name, re.escape(dial_id)), src, re.M), dial_id


def test_the_moved_values_and_the_pairs_order_are_the_code_they_replaced(server):
    rt, K = runtime()
    old = rt.execute(OLD)
    for dom in KERNEL_DOMAINS:
        for name in old[dom].keys():
            got, want = K[dom][name], old[dom][name]
            if lua51.lua_type(want) == "table":
                assert dump(rt, got) == dump(rt, want), name
            else:
                assert float(got).hex() == float(want).hex(), name
    assert dump(rt, K.acute.C) == dump(rt, old.acute.STIM[1])           # the Game set, the default
    for table, fields in OLD_ADAPTERS.items():
        for name, want in fields.items():
            assert float(server.NR.server[table][name]).hex() == float(want).hex(), (table, name)
    E, D = server.NR.server.effects, server.K.drain
    assert (E.REGEN_STANDARD, E.REGEN_REDUCED, E.REGEN_SEVERE, E.REGEN_SLEEPING) == (D.REGEN[1], D.REGEN[2], D.REGEN[3], D.REGEN_SLEEPING)


def test_the_wave_duplicates_are_same_links_and_the_vanilla_scales_fixed():
    raw = raw_rows()
    for dial_id, target in LINKS.items():
        assert raw[dial_id]["same"] == target, dial_id
        assert dials.values()[dial_id] == dials.values()[target], dial_id
    for dial_id, src in FIXED.items():
        assert raw[dial_id].get("fixed") is True and raw[dial_id]["src"] == src, dial_id
    for dial_id in list(FIXED) + list(LINKS):
        with pytest.raises(ValueError):
            dials.set_value(text(), dial_id, "1.2")


def test_a_registry_link_target_moves_every_linked_kernel_field():
    for target, new in (("acute.RISK_BMI_MOD", "19"), ("acute.RISK_BMI_HIGH", "15"), ("acute.RISK_DAYS_MOD", "6"),
                        ("acute.RISK_DAYS_HIGH", "12"), ("aerobic.P_LOW", "0.9"), ("aerobic.EA_THRESHOLD", "25"),
                        ("acute.SHIVER_DEADBAND", "1.2"), ("acute.IU_BG_HI", "2.9"), ("acute.IU_BG_LO", "2.5")):
        _, K = runtime([value_edit(target, new)])
        assert field(K, target) == float(new), target
        for dial_id, t in LINKS.items():
            if t == target:
                assert field(K, dial_id) == float(new), dial_id


def test_the_wave_orderings_and_divisor_floors_hold():
    _, K = runtime()
    raw = raw_rows()
    for dial_id in DIVISORS:
        assert raw[dial_id]["min"] > 0, dial_id
    for lo, hi in DISJOINT:
        assert raw[lo]["max"] < raw[hi]["min"], (lo, hi)
    assert raw["acute.GLYC_MAX"]["min"] >= K.acute.GLYC_REF + K.acute.GLYC_HIGH          # the high target fits the store
    A, E = K.acute, K.effects
    assert A.BG_MIN < A.BG_EXERTION < A.BG_ALC_FAST < A.BG_NORMAL < A.BG_MAX
    assert A.IU_ALC_KNOTS[4][2] <= A.IU_ALC_CAP and A.IU_DEHYD_FROM < A.IU_DEHYD_KNEE
    assert E.PE_BMI_LOW < E.PE_BMI_THIN < E.PE_BMI_OK and E.PE_PROT_3 < E.PE_PROT_2 < E.PE_PROT_OK
    assert E.PE_STARVED_3 < E.PE_STARVED_4 and E.NV_REGRANT <= E.NV_GRANT
    for name in ("ALC_EDGES", "DEBT_EDGES", "DEHYD_EDGES"):
        t = E[name]
        assert all(t[i] < t[i + 1] for i in range(1, len(t))), name
    for name in ("BG_EDGES", "EA_EDGES"):
        t = E[name]
        assert all(t[i] > t[i + 1] for i in range(1, len(t))), name
    assert E.AIM_LO <= 1 <= E.AIM_HI and E.M_LO < E.M_HI and E.R_LO < E.R_HI
    # the top band of each impairment ladder is its kernel cap: a tune of one alone leaves a band past the cap
    assert E.IUS_BANDS * E.IUS_STEP == A.IU_SLEEP_MAX
    assert abs(E.IU_BANDS * E.IU_STEP - A.IU_MAX) < 1e-9


def test_a_registry_half_life_moves_the_caffeine_and_a_registry_knot_moves_the_alcohol_impairment():
    def cafAfter(K):
        a = K.acute.new(0)
        K.acute.caffeine(a, 100, 70, 0)
        K.acute.caffeine(a, 0, 70, 5)
        return a.caf
    _, K = runtime()
    assert abs(cafAfter(K) - 50) < 1e-9 and abs(K.acute.iuAlcohol(0.03) - 0.30) < 1e-12
    _, K = runtime([value_edit("acute.CAF_THALF_H", "10.0"), value_edit("acute.IU_ALC_KNOTS.2.2", "0.5")])
    assert abs(cafAfter(K) - 100 * 2 ** -0.5) < 1e-9 and abs(K.acute.iuAlcohol(0.03) - 0.5) < 1e-12


def test_a_registry_cut_off_moves_the_protein_energy_grade_and_the_energy_availability_band():
    _, K = runtime()
    assert K.effects.peGrade(18.7, 0, None) == 1 and K.effects.peGrade(20, 11, None) == 4
    assert K.effects.eaBand(27) == 1 and K.effects.eaAccrual(27) > 1
    _, K = runtime([value_edit("acute.RISK_BMI_MOD", "19"), value_edit("acute.RISK_DAYS_HIGH", "12"),
                    value_edit("aerobic.EA_THRESHOLD", "25")])
    assert K.effects.peGrade(18.7, 0, None) == 2 and K.effects.peGrade(20, 11, None) == 3
    assert K.effects.eaBand(27) == 0 and K.effects.eaAccrual(27) == 1


def test_a_registry_dead_band_moves_the_cold_hour_and_a_registry_edge_moves_the_dehydration_band():
    _, K = runtime()
    a = K.acute.coldMinute(K.acute.new(0), 1.1, 1)
    assert a.coldH == 1 and K.effects.atOrAbove(0.7, K.effects.DEHYD_EDGES) == 0
    _, K = runtime([value_edit("acute.SHIVER_DEADBAND", "1.2"), value_edit("effects.DEHYD_EDGES.1", "0.5")])
    a = K.acute.coldMinute(K.acute.new(0), 1.1, 1)
    assert a.coldH == 0 and K.effects.atOrAbove(0.7, K.effects.DEHYD_EDGES) == 1


def test_a_registry_stimulant_size_moves_its_set_and_a_registry_sleep_need_moves_the_full_debt():
    _, K = runtime()
    assert K.acute.STIM[1].HANG_H == 3 and K.satiety.SLEEP_DEBT_FULL_H == 2.0
    K.acute.useStimulants(2)
    assert K.effects.intoxTarget(0.1) == 50
    _, K = runtime([value_edit("acute.STIM_GAME_OVERRIDES.HANG_H", "4"),
                    value_edit("acute.STIM_REALISTIC.INTOX_FULL_BAC", "0.25"), value_edit("acute.SLEEP_NEED_H", "8")])
    assert K.acute.STIM[1].HANG_H == 4 and K.satiety.SLEEP_DEBT_FULL_H == 2.5
    K.acute.useStimulants(2)
    assert abs(K.effects.intoxTarget(0.1) - 40) < 1e-9


def test_replay_live_set_constants_writes_a_group_of_array_elements_by_path():
    import replay_live
    _, K = runtime()
    replay_live.set_constants(K, {"energy.CLASS_MET.Fitness": 7})
    assert (K.energy.CLASS_MET.Fitness, K.energy.BAND_MET[3], K.training.BAND1_MET) == (7, 7, 7)
    replay_live.set_constants(K, {"energy.COMPENDIUM.SeatedResting": 1.2})
    assert K.energy.BAND_MET[0.5] == 1.2 and K.energy.COMPENDIUM.SeatedResting == 1.2
    replay_live.set_constants(K, {"energy.BAND_MET.0_5": 1.1})                 # a member names its group too
    assert K.energy.BAND_MET[0.5] == 1.1 and K.energy.COMPENDIUM.SeatedResting == 1.1
    replay_live.set_constants(K, {"fluids.THIRST_KNOTS.2.1": 1.5, "core.HEIGHT_M": 1.8, "acute.SHIVER_DEADBAND": 1.1})
    assert (K.fluids.THIRST_KNOTS[2][1], K.HEIGHT_M, K.acute.COLD_ON) == (1.5, 1.8, 1.1)
    for bad in ("acute.NO_SUCH", "acute.WIDMARK_R", "eff.SOL_CAF_H", "energy.BAND_MET.7"):
        with pytest.raises(ValueError):
            replay_live.set_constants(K, {bad: 1})


def test_replay_live_set_constants_refuses_a_stimulant_set_laid_at_load():
    import replay_live
    _, K = runtime()
    for name in ("acute.STIM_GAME_OVERRIDES.HANG_H", "acute.STIM_REALISTIC.HANG_H"):
        with pytest.raises(ValueError):
            replay_live.set_constants(K, {name: 9})
