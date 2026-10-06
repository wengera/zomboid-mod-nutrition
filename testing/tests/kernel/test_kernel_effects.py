"""The effects kernel (NR_Kernel_Effects.lua, K.effects), Plan 5 Task 6.

NR_Kernel_Effects.lua is a kernel file, so the session `host` loads it through its glob. The composer takes the
declarative table as an argument: these tests load NR_Data_Effects.lua (and NR_Data_Records.lua for the key
order) onto the host as the fixture table, exactly as the adapter will pass NR.data.effects. Every expectation
was recomputed in Python doubles before it was written, the expression beside it; the hand-value ids are the
formulas briefing's section I: I-A1 (stress 0.22 / 0.44 / 0.50), I-B1 / I-B1b (the fatigue offset), I-B2 / I-B2c /
I-B2d (the accrual factors), I-B3 (chi_s through rRec), I-D1 (aimMul), I-D2 (night vision 14.0 / 28.0 / 3.0),
I-E1 (panic 29 / 18), I-F1 (healMul 0.68 / 0.5 / 0.6256, Severity 0.84 / 0.36), I-F3 (coldMul 1.15 / 3.0 / 3.0 / 0.5 /
2.53552 / 1.325), I-F4 (the bruise probability), I-H2 (the seven drains). The briefing's continuous cases (the IU
at 1.0714, caffeine at 107 mg on rNut) are taken at the band's lower edge, which is what the set composes (A2).
"""
import math
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")

TOL = 1e-12
BI = {"caf": 1, "wd": 2, "bac": 3, "alc": 4, "hang": 5, "bg": 6, "iuS": 7, "debt": 8, "iu": 9, "dehyd": 10,
      "hypo": 11, "ex": 12}


def _load(host, path):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@" + os.path.basename(path))()


@pytest.fixture(scope="module")
def kh(host):
    for name in ("NR_Data_Nutrients.lua", "NR_Data_Records.lua", "NR_Data_Effects.lua"):
        _load(host, os.path.join(SHARED, name))
    return host


def _keys(h):
    order = h.G.NutritionRevamp.data.records.ORDER
    return [order[i] for i in range(1, len(order) + 1)]


def _nut(h, **over):
    """A full record.nutrients: every key replete, rung 0; over maps key -> dict of fields."""
    d = {k: {"g": 1, "x": 0, "ah": 0, "e24": 0} for k in _keys(h)}
    for k, v in over.items():
        d[k].update(v)
    return h.table(d)


def _b(h, **over):
    d = {i: 0 for i in range(1, 13)}
    for k, v in over.items():
        d[BI[k]] = v
    return h.table(d)


def _compose(h, nut=None, b=None, pe=1, ea=30, flags=None, sev=1, bonus=False, vitd=False, E=None):
    E = E if E is not None else h.K.effects.new()
    h.K.effects.compose(E, h.G.NutritionRevamp.data.effects, nut if nut is not None else _nut(h),
                        b if b is not None else _b(h), pe, ea, h.table(flags or {}), sev, bonus, vitd)
    return E


def _py(h, E):
    return h.py(E)


# --- constants and the fresh record -------------------------------------------------------------------------

def test_new_is_j1s_table(kh):
    e = kh.py(kh.K.effects.new())
    assert e["ev"] == 1 and e["epoch"] == 0
    assert e["key"] == {"ep": -1, "day": -1, "dials": 0, "b": {i: 0 for i in range(1, 13)}}
    assert (e["aimMul"], e["fOff"], e["solAddH"], e["solMul"], e["pe"], e["ea"], e["nvDays"]) == (1, 0, 0, 1, 1, 30, 0)
    assert e["own"] == {"nv": False, "ss": False}
    assert (e["lethal"], e["intoxTarget"], e["tempTarget"], e["mAcc"], e["rRec"]) == (0, 0, 0, 1, 1)
    assert e["nightVision"] is False and e["shortSighted"] is False
    two = kh.K.effects.new()
    assert two.key.b != kh.K.effects.new().key.b                          # a fresh table each call


def test_new_carries_every_surface_of_the_table_at_its_identity(kh):
    e = kh.py(kh.K.effects.new())
    for name, s in kh.py(kh.G.NutritionRevamp.data.effects.SURF).items():
        assert e[name] == s["id"], name


def test_sat_c_gives_the_tables_caffeine_literals(kh):
    T = kh.G.NutritionRevamp.data.effects.ROWS
    got = {}
    for i in range(1, len(T) + 1):
        row = T[i]
        if row.src == "caf":
            for j in range(1, len(row.list) + 1):
                if row.list[j].s == "rNut":
                    got[row.at] = row.list[j].v
    assert sorted(got) == list(range(1, 17))
    for n, v in got.items():
        assert v == pytest.approx(1 - 0.15 * kh.K.effects.satC(50 * n), abs=1e-15), n


def test_the_band_index_is_the_twelve(kh):
    assert kh.py(kh.K.effects.B) == BI
    assert kh.K.effects.NB == 12


# --- the band vector ------------------------------------------------------------------------------------------

ACUTE = {"caf": 0, "wd": 0, "cafTol": 0, "bac": 0, "alcPeak": 0, "hang": 0, "bg": 5.0, "iuSleep": 0, "debtH": 0,
         "iu": 0, "exEma": 0}
FLUIDS = {"dehydPct": 0, "naPlasma": 140}


def _bands(h, **over):
    a = dict(ACUTE)
    f = dict(FLUIDS)
    for k, v in over.items():
        (f if k in f else a)[k] = v
    b = h.table({i: -1 for i in range(1, 13)})
    out = h.K.effects.bands(b, h.table(a), h.table(f))
    return {name: out[i] for name, i in BI.items()}


@pytest.mark.parametrize("field,value,band,expect", [
    ("caf", 49.999, "caf", 0), ("caf", 50, "caf", 1), ("caf", 799.9, "caf", 15), ("caf", 800, "caf", 16),
    ("caf", 5000, "caf", 16),
    ("alcPeak", 0.0734, "alc", 0), ("alcPeak", 0.0735, "alc", 1), ("alcPeak", 0.1249, "alc", 1), ("alcPeak", 0.125, "alc", 2),
    ("bac", 0, "bac", 0), ("bac", 1e-9, "bac", 1),
    ("hang", 0, "hang", 0), ("hang", 1, "hang", 1),
    ("bg", 3.5, "bg", 0), ("bg", 3.4999, "bg", 1), ("bg", 3.0, "bg", 1), ("bg", 2.9999, "bg", 2), ("bg", 2.6, "bg", 2),
    ("bg", 2.5999, "bg", 3),
    ("iuSleep", 0.1249, "iuS", 0), ("iuSleep", 0.125, "iuS", 1), ("iuSleep", 1.4999, "iuS", 11), ("iuSleep", 1.5, "iuS", 12),
    ("iuSleep", 2.0, "iuS", 12),
    ("debtH", 3.999, "debt", 0), ("debtH", 4, "debt", 1), ("debtH", 7.999, "debt", 1), ("debtH", 8, "debt", 2),
    ("iu", 0.0999, "iu", 0), ("iu", 0.1, "iu", 1), ("iu", 0.3, "iu", 3), ("iu", 0.7, "iu", 7), ("iu", 2.4, "iu", 24),
    ("iu", 2.5, "iu", 25), ("iu", 3.0, "iu", 25),
    ("naPlasma", 135, "hypo", 0), ("naPlasma", 134.9, "hypo", 1), ("naPlasma", 120, "hypo", 1), ("naPlasma", 119.9, "hypo", 2),
    ("naPlasma", 112, "hypo", 2), ("naPlasma", 111.9, "hypo", 3),
    ("exEma", 7.4999, "ex", 0), ("exEma", 7.5, "ex", 1), ("exEma", 29.999, "ex", 3), ("exEma", 30, "ex", 4), ("exEma", 100, "ex", 4),
])
def test_each_band_edge_both_ways(kh, field, value, band, expect):
    assert _bands(kh, **{field: value})[band] == expect


@pytest.mark.parametrize("pct,expect", [(0.999, 0), (1, 1), (1.4999, 1), (1.5, 2), (1.9999, 2), (2, 3), (2.4999, 3),
                                        (2.5, 4), (2.9999, 4), (3, 5), (3.9999, 5), (4, 6), (5.9999, 6), (6, 7),
                                        (9.9999, 7), (10, 8), (25, 8)])
def test_the_dehydration_edges_both_ways(kh, pct, expect):
    assert _bands(kh, dehydPct=pct)["dehyd"] == expect


@pytest.mark.parametrize("wd,tol,expect", [(1, 0.12, 0), (1, 0.125, 1), (0.5, 1, 2), (1, 0.6, 2), (1, 1, 4), (0, 1, 0)])
def test_the_withdrawal_band_is_wd_times_tolerance(kh, wd, tol, expect):
    assert _bands(kh, wd=wd, cafTol=tol)["wd"] == expect                  # round(4 x wd x cafTol)


def test_a_neutral_record_bands_to_zeros(kh):
    assert set(_bands(kh).values()) == {0}


def test_step_floors_and_clamps(kh):
    E = kh.K.effects
    assert E.step(-5, 50, 16) == 0
    assert E.step(0.3, 0.1, 25) == 3                                      # 0.3 / 0.1 = 2.9999999999999996 without the guard


# --- the change key -----------------------------------------------------------------------------------------

def test_changed_is_false_on_an_identical_key_and_true_on_each_component(kh):
    E = kh.K.effects
    b = _b(kh, caf=3, iu=7, dehyd=2)
    key = kh.K.effects.new().key
    assert E.changed(key, 5, 2, 1000, b) is True                          # the fresh key never matches
    E.stampKey(key, 5, 2, 1000, b)
    assert E.changed(key, 5, 2, 1000, b) is False
    assert E.changed(key, 5, 2, 1000, _b(kh, caf=3, iu=7, dehyd=2)) is False   # equal values, another table
    assert E.changed(key, 6, 2, 1000, b) is True
    assert E.changed(key, 5, 3, 1000, b) is True
    assert E.changed(key, 5, 2, 1001, b) is True
    for name in BI:
        other = _b(kh, caf=3, iu=7, dehyd=2)
        other[BI[name]] = other[BI[name]] + 1
        assert E.changed(key, 5, 2, 1000, other) is True, name
    b[1] = 9
    assert key.b[1] == 3                                                  # stampKey copied, it did not alias


# --- the closed-day composites ------------------------------------------------------------------------------

@pytest.mark.parametrize("bmi,starved,prot,expect", [
    (22, 0, 1.0, 1), (18.5, 5, 0.8, 1), (18.49, 0, 1.0, 2), (17, 0, 1.0, 2), (16.99, 0, 1.0, 3), (16, 0, 1.0, 3),
    (15.99, 0, 1.0, 4), (22, 6, 1.0, 3), (22, 10, 1.0, 3), (22, 11, 1.0, 4), (17.5, 6, 1.0, 3), (15, 6, 1.0, 4),
    (0, 0, 1.0, 1), (0, 6, 1.0, 3),                                       # BMI 0 = not yet closed: the starved days alone
    (22, 0, 0.79, 2), (22, 0, 0.6, 2), (22, 0, 0.59, 3), (22, 0, 0.4, 3), (22, 0, 0.39, 4),
    (22, 0, None, 1), (22, 0, -1, 1), (17.5, 0, 0.5, 3),                  # unknown protein reads 1; max of the sides
])
def test_pe_grade_on_the_s0115_edges(kh, bmi, starved, prot, expect):
    assert kh.K.effects.peGrade(bmi, starved, prot) == expect


@pytest.mark.parametrize("ea,expect", [(45, 0), (30, 0), (29.99, 1), (20, 1), (19.99, 2), (10, 2), (9.99, 3), (-5, 3)])
def test_ea_band(kh, ea, expect):
    assert kh.K.effects.eaBand(ea) == expect


@pytest.mark.parametrize("ea,expect", [(35, 1.0), (30, 1.0), (25, 1.0833333333333333), (20, 1.1666666666666667),
                                       (15, 1.25), (10, 1.325), (5, 1.4), (0, 1.4)])
def test_ea_accrual_i_b2c(kh, ea, expect):
    assert kh.K.effects.eaAccrual(ea) == pytest.approx(expect, abs=TOL)


# --- the composer ---------------------------------------------------------------------------------------------

def test_compose_at_neutral_is_every_identity(kh):
    e = _py(kh, _compose(kh))
    T = kh.py(kh.G.NutritionRevamp.data.effects.SURF)
    for name, s in T.items():
        assert e[name] == s["id"], name
    assert e["aimMul"] == 1 and e["epoch"] == 1


def test_compose_is_pure_and_counts_its_rebuilds(kh):
    E = kh.K.effects.new()
    nut = _nut(kh, iron={"g": 3}, vitC={"g": 4})
    b = _b(kh, dehyd=4, caf=8, iuS=8, iu=12)
    flags = {"bgroupMax": 4, "coldCredit": False}
    _compose(kh, nut=nut, b=b, pe=3, ea=15, flags=flags, sev=1.5, E=E)
    first = _py(kh, E)
    _compose(kh, nut=nut, b=b, pe=3, ea=15, flags=flags, sev=1.5, E=E)
    second = _py(kh, E)
    assert first["epoch"] == 1 and second["epoch"] == 2
    first.pop("epoch")
    second.pop("epoch")
    assert first == second


def test_compose_leaves_the_machine_surfaces(kh):
    E = kh.K.effects.new()
    E.drain = 0.1
    E.nightVision = True
    _compose(kh, E=E)
    assert E.drain == 0.1 and E.nightVision is True


def test_i_a1_stress_and_its_severity(kh):
    b = _b(kh, hang=1, dehyd=2)
    flags = {"bgroupMax": 4}
    assert _compose(kh, b=b, flags=flags).stressTarget == pytest.approx(0.22, abs=TOL)       # 0.06 + 0.10 + 0.06
    assert _compose(kh, b=b, flags=flags, sev=2).stressTarget == pytest.approx(0.44, abs=TOL)
    assert _compose(kh, b=b, flags=flags, sev=3).stressTarget == 0.50                         # 0.66 clamped
    assert _compose(kh, b=b, flags={"bgroupMax": 3}).stressTarget == pytest.approx(0.19, abs=TOL)
    assert _compose(kh, b=_b(kh, bac=1)).stressTarget == 0                                    # never during


@pytest.mark.parametrize("iu,expect", [(0, 1.0), (0.2, 1.05), (0.5, 1.125), (1.0, 1.25), (2.0, 1.5), (2.4, 1.6), (2.5, 1.6)])
def test_i_d1_aim_mul_through_the_iu_band(kh, iu, expect):
    band = _bands(kh, iu=iu)["iu"]
    assert _compose(kh, b=_b(kh, iu=band)).aimMul == pytest.approx(expect, abs=TOL)


def test_i_e1_panic_from_sleep_loss_and_caffeine_with_the_exercise_credit(kh):
    b = _b(kh, iuS=8, caf=8)                                              # 24 h awake (1 IU), 400 mg
    assert _compose(kh, b=b).panicTarget == 29                            # 14 + 15
    b = _b(kh, iuS=8, caf=8, ex=4)                                        # 45 min moderate: exQ 1
    assert _compose(kh, b=b).panicTarget == 18                            # 29 - 11
    assert _compose(kh, b=_b(kh, caf=16, iuS=12)).panicTarget == 64      # 64 + 20 clamped one under level 3
    assert _compose(kh, b=_b(kh, ex=4)).panicTarget == 0                  # a credit never makes a bonus
    e = _compose(kh, b=_b(kh, iuS=12, wd=4), vitd=True, nut=_nut(kh, vitD={"g": 4}))
    assert e.unhappyTarget == pytest.approx(25 + 10 + 4, abs=TOL)


def test_i_b2_the_accrual_product(kh):
    nut = _nut(kh, iron={"g": 3})
    e = _compose(kh, nut=nut, b=_b(kh, dehyd=4), ea=20)
    assert e.mNut == pytest.approx(1.5669500000000003, abs=TOL)           # 1.11 x 1.21 x 1.1666666666666667
    assert kh.K.acute.chiW(0, e.mNut) == pytest.approx(11.614920705829794, abs=1e-9)
    # anaemia replaces the depleted-iron row (unless): 1.25, not 1.25 x 1.11
    e = _compose(kh, nut=nut, flags={"anaemia": True})
    assert e.mNut == pytest.approx(1.25, abs=TOL)
    e = _compose(kh, b=_b(kh, wd=4, hang=1))
    assert e.mNut == pytest.approx(1.2 * 1.15, abs=TOL)
    e = _compose(kh, b=_b(kh, dehyd=8), ea=0, nut=nut, flags={"anaemia": True}, sev=3)
    assert e.mNut == 2.0                                                  # clamped


def test_i_b3_recovery_through_chi_s(kh):
    chiS = kh.K.acute.chiS
    rE = kh.K.effects.rEngine
    r = _compose(kh, flags={"allReplete": True}, bonus=True).rNut
    assert chiS(r * rE(1, 1)) == pytest.approx(4.0, abs=1e-12)            # BalanceBonus 1.05
    assert _compose(kh, flags={"allReplete": True}, bonus=False).rNut == 1
    assert _compose(kh, flags={"allReplete": True}, bonus=True, sev=0).rNut == 1.05     # a bonus is not scaled
    assert chiS(rE(0.6, 1)) == pytest.approx(7.000000000000001, abs=1e-12)              # the floor bed
    assert chiS(rE(1.15, 1.4)) == pytest.approx(2.6086956521739135, abs=1e-12)          # goodBedPillow, night owl
    r = _compose(kh, b=_b(kh, caf=3)).rNut                                # saturated caffeine 0.85
    assert chiS(r * rE(1, 0.5 / 1.18)) == pytest.approx(11.661176470588234, abs=1e-9)  # insomniac, needs more sleep
    assert chiS(_compose(kh, b=_b(kh, alc=2)).rNut) == pytest.approx(5.25, abs=1e-12)  # alcohol band 2
    assert _compose(kh, b=_b(kh, caf=1)).rNut == 0.9641522029372497       # I-B3c at 50 mg


def test_the_exercise_credit_and_the_vigorous_replacement(kh):
    assert _compose(kh, b=_b(kh, ex=4)).rNut == pytest.approx(1.1, abs=TOL)
    assert _compose(kh, b=_b(kh, ex=4), flags={"boutVig": True}).rNut == pytest.approx(0.95, abs=TOL)
    assert _compose(kh, b=_b(kh, ex=2), flags={"boutVig": False}).rNut == pytest.approx(1.05, abs=TOL)


def test_i_f1_heal_mul_and_its_severity(kh):
    def heal(pe, c, z, sev=1):
        return _compose(kh, nut=_nut(kh, vitC={"g": c}, zinc={"g": z}), pe=pe, sev=sev).healMul
    assert heal(3, 3, 1) == pytest.approx(0.68, abs=TOL)                  # 0.80 x 0.85
    assert heal(4, 4, 4) == 0.5                                           # 0.74 x 0.50 x 0.85 = 0.3145 clamped
    assert heal(3, 3, 3) == pytest.approx(0.6256, abs=TOL)                # 0.80 x 0.85 x 0.92
    assert heal(3, 3, 1, sev=0.5) == pytest.approx(0.84, abs=TOL)         # 1 - 0.32 x 0.5
    assert heal(3, 3, 1, sev=2) == 0.5                                    # 0.36 clamped to the floor
    assert kh.K.effects.sevScale("mul", 0.68, 2, None) == pytest.approx(0.36, abs=TOL)
    assert heal(1, 1, 1) == 1.0 and heal(2, 2, 2) == pytest.approx(0.92, abs=TOL)
    assert _compose(kh, pe=4).infectMul == pytest.approx(2.30, abs=TOL)
    assert _compose(kh, pe=4, sev=0).infectMul == 1


def test_i_f3_cold_mul(kh):
    nut4 = _nut(kh, vitC={"g": 4})
    assert _compose(kh).coldMul == 1.0
    assert _compose(kh, nut=nut4).coldMul == pytest.approx(1.15, abs=TOL)
    assert _compose(kh, ea=15, b=_b(kh, debt=1)).coldMul == 3.0           # 2.2 x 1.6 = 3.52 clamped
    assert _compose(kh, ea=5, b=_b(kh, debt=2)).coldMul == 3.0            # 3.0 x 2.5 = 7.5 clamped
    assert _compose(kh, flags={"coldCredit": True}).coldMul == 0.5
    both = _nut(kh, vitC={"g": 4}, vitD={"g": 4})
    assert _compose(kh, nut=both, ea=25, b=_b(kh, debt=1), vitd=True).coldMul == pytest.approx(2.53552, abs=TOL)
    assert _compose(kh, nut=both, ea=25, b=_b(kh, debt=1), vitd=False).coldMul == pytest.approx(1.15 * 1.3 * 1.6, abs=TOL)
    vd = _nut(kh, vitD={"g": 4})
    e = _compose(kh, nut=vd, b=_b(kh, debt=2), flags={"coldCredit": True}, vitd=True)
    assert e.coldMul == pytest.approx(1.3250000000000002, abs=TOL)        # 0.5 x 2.5 x 1.06
    e = _compose(kh, nut=vd, b=_b(kh, debt=2), flags={"coldCredit": True}, vitd=True, sev=0)
    assert e.coldMul == 0.5                                               # the penalties scale away, the credit stays


def test_the_vitamin_d_rows_are_gated(kh):
    vd = _nut(kh, vitD={"g": 4})
    off = _compose(kh, nut=vd)
    assert off.unhappyTarget == 0 and off.coldMul == 1
    on = _compose(kh, nut=vd, vitd=True)
    assert on.unhappyTarget == 4 and on.coldMul == pytest.approx(1.06, abs=TOL)
    assert _compose(kh, nut=_nut(kh, vitD={"g": 3}), vitd=True).unhappyTarget == 2


def test_an_unknown_gate_is_off_and_a_flag_matches_only_true(kh):
    t = kh.rt.eval("""function()
        return { SURF = { mNut = { op = "mul", id = 1, lo = 1, hi = 2 } },
                 ROWS = { { src = "anaemia", on = "flag", gated = "Other", list = { { ch = "stat", s = "mNut", v = 1.5, row = "S1120" } } },
                          { src = "anaemia", on = "flag", list = { { ch = "stat", s = "mNut", v = 1.25, row = "S1120" } } } } }
    end""")()
    E = kh.K.effects.new()
    kh.K.effects.compose(E, t, _nut(kh), _b(kh), 1, 30, kh.table({"anaemia": True}), 1, True, True)
    assert E.mNut == 1.25                                                 # the Other-gated row never folds
    kh.K.effects.compose(E, t, _nut(kh), _b(kh), 1, 30, kh.table({"anaemia": 1}), 1, True, True)
    assert E.mNut == 1                                                    # a non-boolean flag does not match nil
    assert kh.K.effects.atMatch(None, kh.table({1: 2, 2: 3})) is False


def test_i_f4_the_bruise_probability(kh):
    e = _compose(kh, nut=_nut(kh, vitC={"g": 4}))
    assert e.bruise == 3.4722222222222224e-4
    assert 1 - (1 - e.bruise) ** 1440 == pytest.approx(0.39352200042286156, abs=1e-12)
    assert _compose(kh, nut=_nut(kh, vitC={"g": 3})).bruise == 0
    assert e.bleedMul == 1.25 and _compose(kh, nut=_nut(kh, vitC={"g": 3})).bleedMul == pytest.approx(1.10, abs=TOL)


def test_the_food_sickness_rungs(kh):
    def sick(**kw):
        return _compose(kh, **kw).foodSickTarget
    assert sick(nut=_nut(kh, iron={"x": 1})) == 30
    assert sick(nut=_nut(kh, vitB6={"x": 2})) == 55
    assert sick(nut=_nut(kh, iron={"x": 3})) == 85
    assert sick(nut=_nut(kh, zinc={"x": 1}, vitA={"x": 2})) == 55
    assert sick(b=_b(kh, hypo=2)) == 55 and sick(b=_b(kh, hypo=3)) == 85 and sick(b=_b(kh, hypo=1)) == 0
    assert sick(flags={"refeedEvent": True}) == 55
    e = _compose(kh, nut=_nut(kh, iron={"x": 3}), b=_b(kh, hypo=3), flags={"refeedEvent": True})
    assert e.foodSickTarget == 85 and e.poisonTarget == 0                 # ruling 12; T1-1


def test_temperature_speed_fatigue_offset_and_short_sight(kh):
    e = _compose(kh, nut=_nut(kh, iron={"g": 4}), b=_b(kh, bg=3))
    assert e.tempOffset == pytest.approx(-0.4, abs=TOL)
    assert kh.K.effects.tempOffset(e) == e.tempOffset
    assert _compose(kh, b=_b(kh, dehyd=6)).tempHeat == pytest.approx(0.3, abs=TOL)
    assert _compose(kh, b=_b(kh, dehyd=4)).tempHeat == pytest.approx(0.075, abs=TOL)
    e = _compose(kh, b=_b(kh, bg=2, iu=22))
    assert e.speedMul == pytest.approx(0.90, abs=TOL)                     # min(0.92, 0.90)
    assert _compose(kh, b=_b(kh, bg=3, hypo=2, dehyd=7)).speedMul == pytest.approx(0.85, abs=TOL)
    assert _compose(kh, b=_b(kh, dehyd=6, bg=3)).fOffNut == 0.15          # 0.10 + 0.10 capped
    assert _compose(kh, b=_b(kh, dehyd=3)).fOffNut == pytest.approx(0.06, abs=TOL)
    vitA = _nut(kh, vitA={"g": 4})
    assert _compose(kh, nut=vitA).shortSighted is True
    assert _compose(kh, nut=vitA, sev=0.5).shortSighted is False          # ruling 7
    assert _compose(kh, nut=_nut(kh, vitA={"g": 3})).shortSighted is False
    assert kh.K.effects.sevScale("or", True, 0.5, None) is True
    assert kh.K.effects.sevScale("max", 30, 2, None) == 30
    assert kh.K.effects.sevScale("min", 0.85, 2, None) == 0.85


def test_bgroup_max(kh):
    assert kh.K.effects.bgroupMax(_nut(kh)) == 1
    assert kh.K.effects.bgroupMax(_nut(kh, folate={"g": 3}, vitB12={"g": 4}, vitC={"g": 4})) == 4
    assert kh.py(kh.K.effects.BGROUP) == {1: "thiamine", 2: "riboflavin", 3: "niacin", 4: "vitB6", 5: "folate", 6: "vitB12"}


# --- the per-minute scalars ---------------------------------------------------------------------------------

def test_i_b1_the_fatigue_offset(kh):
    f = kh.K.effects.fOff
    circ1 = 0.12 * math.cos(2 * math.pi * (1 - 4) / 24)                  # 0.08485281374238571
    assert 0.5 + circ1 + f(6, 107, 0, 0) == pytest.approx(0.4691329693844091, abs=TOL)
    assert f(0, 107, 1, 0) == pytest.approx(-0.05828793774319066, abs=TOL)
    assert f(0, 200, 0, 0) == pytest.approx(-0.2, abs=TOL)
    assert f(0, 400, 0, 0) == pytest.approx(-0.2545454545454545, abs=TOL)
    assert f(0, 400, 1, 0) == pytest.approx(-0.10181818181818181, abs=TOL)
    assert f(40, 0, 0, 0.15) == pytest.approx(0.25, abs=TOL)              # the debt term caps at 0.10


def test_sat_c(kh):
    s = kh.K.effects.satC
    assert s(0) == 0 and s(32.1) == 0 and s(107) == 1 and s(500) == 1
    assert s(50) == pytest.approx(0.23898531375166884, abs=TOL)


@pytest.mark.parametrize("e,expect", [(1, 1.0), (0.7, 1.0), (0.5, 1.6666666666666667), (0.25, 2.5), (0, 3.3333333333333335)])
def test_i_b2d_m_engine_endurance(kh, e, expect):
    assert kh.K.effects.mEngine(e, False, 1, 1, 1) == pytest.approx(expect, abs=TOL)


def test_m_engine_factors_and_clamp(kh):
    m = kh.K.effects.mEngine
    assert m(1, True, 1, 1, 1) == pytest.approx(1 / 1.5, abs=TOL)
    assert m(1, False, 1.2, 0.7, 0.5) == pytest.approx(1.2 * 0.7 * 0.5, abs=TOL)
    assert m(0, False, 2, 1.3, 1) == 5.0                                  # 8.67 clamped
    assert m(1, True, 1, 0.7, 0.1) == 0.2                                 # 0.047 clamped


def test_r_engine(kh):
    r = kh.K.effects.rEngine
    assert r(1.15, 1.4) == pytest.approx(1.61, abs=TOL)
    assert r(0.6, 0.3) == 0.25 and r(1.15, 2) == 2.0


# --- night vision and short sight -----------------------------------------------------------------------------

NV_RUN = r"""
function(E, days, vitAg, zincG, ironG, riboG, retOk)
    local K = NutritionRevamp.kernel
    local first = nil
    for m = 1, days * 1440 do
        local want = K.effects.nvMinute(E, vitAg, zincG, ironG, riboG, retOk, 1 / 1440)
        if want and first == nil then
            first = m
        end
    end
    return first
end
"""


def _nv(h, E, days, vitAg=1, zincG=1, ironG=1, riboG=1, retOk=True):
    return h.rt.eval(NV_RUN)(E, days, vitAg, zincG, ironG, riboG, retOk)


def test_i_d2_night_vision_grant_slowed_and_regrant(kh):
    E = kh.K.effects.new()
    first = _nv(kh, E, 15)
    assert abs(first - 20160) <= 1                                        # day 14.0
    assert E.nightVision is True
    E = kh.K.effects.new()
    assert abs(_nv(kh, E, 29, ironG=3) - 2 * 20160) <= 2                  # day 28.0 under iron depletion
    E = kh.K.effects.new()
    assert abs(_nv(kh, E, 29, riboG=4) - 2 * 20160) <= 2                  # and under riboflavin
    E = kh.K.effects.new()
    _nv(kh, E, 15)
    assert kh.K.effects.nvMinute(E, 2, 1, 1, 1, True, 1 / 1440) is False  # withdrawn the first marginal minute
    assert E.nvDays == pytest.approx(11 - 1 / 1440, abs=1e-12)
    assert E.nightVision is False
    regrant = _nv(kh, E, 4)
    assert abs(regrant - 3 * 1440) <= 2                                   # re-granted after 3.0 replete days
    E = kh.K.effects.new()
    _nv(kh, E, 15)
    assert _nv(kh, E, 20, vitAg=2) is None                                # a 20-day lapse
    assert E.nvDays == 0
    assert abs(_nv(kh, E, 15) - 20160) <= 1                               # the full 14 days again


def test_no_night_vision_without_preformed_retinol_or_with_zinc_depleted(kh):
    E = kh.K.effects.new()
    assert _nv(kh, E, 20, retOk=False) is None                            # a carotene-only diet (ruling 6, S0870)
    assert E.nvDays == 0
    E = kh.K.effects.new()
    assert _nv(kh, E, 20, zincG=3) is None
    E = kh.K.effects.new()
    assert _nv(kh, E, 20, vitAg=2) is None


def test_ss_want(kh):
    s = kh.K.effects.ssWant
    assert s(4, 1) is True and s(4, 3) is True
    assert s(4, 0.99) is False and s(3, 1) is False


# --- the drains -----------------------------------------------------------------------------------------------

DRAINS = [0.023148148148148147, 0.00992063492063492, 0.023148148148148147, 0.00496031746031746,
          0.2777777777777778, 0.1388888888888889, 0.06944444444444445]


def _drain(h, nut=None, dehyd=0, na=140, bmi=22, pe=1, bf=0.2, sex=1, kill=True):
    E = h.K.effects.new()
    d = h.K.effects.drain(E, nut if nut is not None else _nut(h), h.table({"dehydPct": dehyd, "naPlasma": na}),
                          h.table({"bmi": bmi}), pe, bf, sex, kill)
    return d, E.lethal, E.drain


def test_i_h2_the_seven_drains(kh):
    hours = [72, 168, 72, 336, 6, 12, 24]
    for i, h in enumerate(hours):
        assert DRAINS[i] == pytest.approx(100 / (h * 60), abs=1e-15), i  # 100 health in h game hours
    assert [kh.K.effects.DRAIN_RATE[i] for i in range(1, 8)] == DRAINS
    assert _drain(kh, pe=4, bf=0.04) == (DRAINS[0], 1, DRAINS[0])
    assert _drain(kh, nut=_nut(kh, vitC={"g": 4, "ah": 720})) == (DRAINS[1], 2, DRAINS[1])
    assert _drain(kh, nut=_nut(kh, thiamine={"g": 4, "ah": 168})) == (DRAINS[2], 3, DRAINS[2])
    assert _drain(kh, nut=_nut(kh, niacin={"g": 4, "ah": 1440})) == (DRAINS[3], 4, DRAINS[3])
    assert _drain(kh, na=111.9) == (DRAINS[4], 5, DRAINS[4])
    assert _drain(kh, dehyd=10) == (DRAINS[5], 6, DRAINS[5])
    assert _drain(kh, nut=_nut(kh, iron={"x": 3})) == (DRAINS[6], 7, DRAINS[6])


def test_the_drain_gates_and_the_max(kh):
    assert _drain(kh) == (0, 0, 0)
    assert _drain(kh, pe=4, bf=0.05)[1] == 0                              # fat above the male floor
    assert _drain(kh, pe=4, bf=0.09, sex=2)[1] == 1                       # under the female floor 0.10
    assert _drain(kh, pe=4, bf=0.2, bmi=11.9)[1] == 1                     # BMI under 12
    assert _drain(kh, pe=4, bf=0.2, bmi=0)[1] == 0                        # BMI unknown
    assert _drain(kh, pe=3, bf=0.01)[1] == 0                              # only at pe 4
    assert _drain(kh, nut=_nut(kh, vitC={"g": 4, "ah": 719.9}))[1] == 0
    assert _drain(kh, nut=_nut(kh, vitC={"g": 3, "ah": 9999}))[1] == 0
    assert _drain(kh, nut=_nut(kh, thiamine={"g": 4, "ah": 167}))[1] == 0
    assert _drain(kh, nut=_nut(kh, niacin={"g": 4, "ah": 1439}))[1] == 0
    assert _drain(kh, na=112)[1] == 0 and _drain(kh, dehyd=9.99)[1] == 0
    assert _drain(kh, nut=_nut(kh, iron={"x": 2}))[1] == 0
    both = _nut(kh, vitC={"g": 4, "ah": 800}, thiamine={"g": 4, "ah": 200}, iron={"x": 3})
    assert _drain(kh, nut=both, na=100, dehyd=12, pe=4, bf=0.01)[:2] == (DRAINS[4], 5)   # max, not a sum
    assert _drain(kh, nut=_nut(kh, thiamine={"g": 4, "ah": 200}), pe=4, bf=0.01)[:2] == (DRAINS[0], 1)  # a tie keeps the first
    assert _drain(kh, nut=both, na=100, kill=False) == (0, 0, 0)          # DeficienciesCanKill off


def test_intox_target(kh):
    t = kh.K.effects.intoxTarget
    assert t(0) == 0 and t(0.1) == pytest.approx(50, abs=TOL) and t(0.2) == 100 and t(0.35) == 100
    assert t(-0.01) == 0
    assert t(0.02) == pytest.approx(10, abs=TOL)                          # the Drunk moodle's first step at 0.02 %


def test_the_cold_credit_gate(kh):
    c = kh.K.effects.coldCredit
    assert c(1, 200, 0, 10, 0.25) is True                                 # a hard day (HARD_DAY_MIN 10)
    assert c(1, 200, 60, 0, 0.25) is True                                 # an hour of moderate work
    assert c(1, 200, 59, 9, 0.25) is False                                # not exerting
    assert c(2, 500, 120, 30, 2) is False                                 # not replete
    assert c(1, 199, 120, 30, 2) is False                                 # under 200 mg/d (S0980)
    assert c(1, 500, 120, 30, 0.24) is False                              # not cold-exposed
