"""The generic nutrient record engine (NR_Kernel_Nutrients.lua), Plan 4 Task 6.

NR_Kernel_Nutrients.lua is a kernel file (its name is NR_Kernel*), so the session `host` fixture loads it
through its glob and already has NutritionRevamp.kernel.nutrients. The records are injected: every test
builds a small fixture record table `{ ORDER = {...}, REC = {...} }` in Lua and the kernel never names
NR.data. Every expected number below was computed in Python doubles first; the expression sits beside it.

The model (formulas briefing A0, A3, A7, A8; plan rulings 2, 4, 5, 18): each pool is the fraction p of its
replete store, dp/dt = kEff (i/R - p), stepped in the zero-order-hold form p = p e + (1 - e) i/R with
e = exp(-kEff dtD) (exact at constant intake within a step; the controller's refinement of A0's impulse
form, whose drift at i = R measured 7.6e-7 per day of one-minute steps); the ladder {0.70, 0.45, 0.25}
with 0.02 hysteresis on the way up (game choices, ruling 4); the onset dial on records slower than 90 days
replete-to-clinical (ruling 5); e24 the 1-day exponential sum of the ingested amount, rung 1 at the UL,
rung 2 on a chronic threshold held 7 days or a store threshold; the acute tests per eat (ruling 18).
"""
import math

import pytest

TOL = 1e-9

# The fixture records (amendments: the field-name contract Task 7 follows).
RECORDS = r"""
{
  ORDER = { "vitC", "vitE" },
  REC = {
    vitC = { key = "vitC", unit = "mg", kind = "pool", R = { 90, 75 }, k = 0.047428,
             ladder = { 0.70, 0.45, 0.15 }, pCap = 1.0, ul = 2000 },
    vitE = { key = "vitE", unit = "mg", kind = "ledger" },
  },
}
"""


def _records(host, src=RECORDS):
    return host.rt.eval(src)


def _ctx(host, **kw):
    d = dict(sex=1, w=80.0, eeMJ=10.0, pDay=100.0)
    d.update(kw)
    return host.table(d)


def _rec(host, src):
    return host.rt.eval(src)


def _s(host, **kw):
    s = host.K.nutrients.newKey()
    for k, v in kw.items():
        s[k] = v
    return s


# ---------------------------------------------------------------------------------------------- constants


def test_constants(host):
    N = host.K.nutrients
    assert [N.LADDER[i] for i in (1, 2, 3)] == [0.70, 0.45, 0.25]
    assert N.HYST == 0.02
    assert N.EXCESS_HOLD_D == 7
    assert N.ACUTE_DECAY_H == 48
    assert N.DIAL_SLOW_DAYS == 90
    assert N.ACUTE_EMPTY_FILL == 0.2
    assert N.ACUTE_EMPTY_MULT == 1.5
    assert N.NV == 1


# -------------------------------------------------------------------------------------------- calibration


def test_calib(host):
    # math.log(1/0.15)/40 = 0.047427999622147034 (vitamin C, briefing J 0.0474280)
    assert host.K.nutrients.calib(0.15, 40) == pytest.approx(0.047427999622147034, abs=1e-12)


def test_k_from_half_life(host):
    # math.log(2)/13.5 = 0.05134423559703299 (briefing J 0.0513442; the amendments' 0.05134420 is a rounding)
    assert host.K.nutrients.kFromHalfLife(13.5) == pytest.approx(0.05134423559703299, abs=1e-12)


def test_calib_at(host):
    # -math.log((0.5 - 4/11)/(1 - 4/11))/49 = 0.031437653896880594 (the formula at i0/R = 4/11 exactly)
    assert host.K.nutrients.calibAt(0.5, 49, 4 / 11) == pytest.approx(0.031437653896880594, abs=1e-12)
    # briefing J's 0.0310169 is the same formula at i0/R rounded to 0.36:
    # -math.log((0.5 - 0.36)/(1 - 0.36))/49 = 0.031016926...
    assert host.K.nutrients.calibAt(0.5, 49, 0.36) == pytest.approx(0.0310169, abs=1e-6)


def test_f_from_threshold(host):
    # 0.5/1.2 = 0.4166666666666667
    assert host.K.nutrients.fFromThreshold(0.5, 1.2) == pytest.approx(0.4166666666666667, abs=1e-12)


# ------------------------------------------------------------------------------------------------- state


def test_new_state(host):
    st = host.py(host.K.nutrients.newState(_records(host)))
    assert st["nv"] == 1
    assert st["epoch"] == 0
    assert st["allReplete"] is True
    assert st["ironGrade"] == 1
    assert st["anaemia"] is False
    assert st["vitDClinical"] is False
    fresh = dict(p=1, p2=1, g=1, gl=1, ah=0, x=0, e24=0, dmg=0, ext=0, ax=0, axr=0)
    assert st["vitC"] == fresh
    assert st["vitE"] == fresh


# ----------------------------------------------------------------------------------- requirement and dial


def test_requirement_scales(host):
    N = host.K.nutrients
    ctx = _ctx(host, sex=2, eeMJ=10.0, pDay=100.0, w=70.0)
    assert N.requirement(_rec(host, "{ R = { 90, 75 } }"), ctx) == 75
    assert N.requirement(_rec(host, "{ R = { 90, 75 }, absorb = 0.8 }"), ctx) == pytest.approx(60.0, abs=TOL)
    # thiamine-like: 0.12 mg/MJ x 10 MJ = 1.2
    assert N.requirement(_rec(host, '{ R = { 0.12, 0.12 }, scale = "perMJ" }'), ctx) == pytest.approx(1.2, abs=TOL)
    # 0.02 per g protein x 100 g = 2.0
    assert N.requirement(_rec(host, '{ R = { 0.02, 0.02 }, scale = "perProteinG" }'), ctx) == pytest.approx(2.0, abs=TOL)
    # vitamin K at 1 ug/kg x 70 kg = 70
    assert N.requirement(_rec(host, '{ R = { 1, 1 }, scale = "perKg" }'), ctx) == pytest.approx(70.0, abs=TOL)
    # B6: max(1.3, 0.016 x 100) = 1.6; at 50 g protein max(1.3, 0.8) = 1.3
    b6 = _rec(host, '{ R = { 1.3, 1.3 }, scale = "perProteinGMax", Rscale = 0.016 }')
    assert N.requirement(b6, ctx) == pytest.approx(1.6, abs=TOL)
    assert N.requirement(b6, _ctx(host, pDay=50.0)) == pytest.approx(1.3, abs=TOL)
    # a record with no requirement (a ledger) reads 0
    assert N.requirement(_rec(host, '{ kind = "ledger" }'), ctx) == 0


def test_dial_exponent(host):
    N = host.K.nutrients
    # B12: ln(1/0.10)/0.001 = 2302.585 d > 90 -> 1; vitC: ln(1/0.15)/0.0474 = 40.02 d -> 0
    b12 = _rec(host, "{ k = 0.001, ladder = { 0.70, 0.45, 0.10 } }")
    vitc = _rec(host, "{ k = 0.0474, ladder = { 0.70, 0.45, 0.15 } }")
    assert N.dialExp(b12) == 1
    assert N.dialExp(vitc) == 0
    # no ladder: the generic clinical 0.25; ln(4)/0.01 = 138.6 d -> 1
    assert N.dialExp(_rec(host, "{ k = 0.01 }")) == 1
    # no k (a counter or a ledger): never dialled
    assert N.dialExp(_rec(host, '{ kind = "ledger" }')) == 0
    # an explicit exponent wins
    assert N.dialExp(_rec(host, "{ k = 0.001, dialExp = 0 }")) == 0


def test_k_eff(host):
    N = host.K.nutrients
    b12 = _rec(host, "{ k = 0.001, ladder = { 0.70, 0.45, 0.10 } }")
    vitc = _rec(host, "{ k = 0.0474, ladder = { 0.70, 0.45, 0.15 } }")
    assert N.kEff(b12, 0.001, 10) == pytest.approx(0.01, abs=1e-15)
    assert N.kEff(vitc, 0.0474, 10) == 0.0474


# ------------------------------------------------------------------------------------------------ pool step


def _vitc(host):
    return _rec(host, '{ kind = "pool", R = { 90, 75 }, k = 0.047428, ladder = { 0.70, 0.45, 0.15 }, pCap = 1.0 }')


def test_step_pool_zero_intake_40_days(host):
    N = host.K.nutrients
    k = 0.047427999622147034
    s = _s(host)
    rec = _vitc(host)
    for _ in range(40 * 24):
        N.stepPool(s, rec, 0, 90, k, 60 / 1440)
    # Python doubles, the same loop: 0.14999999999999242; exp(-k 40) = 0.15
    assert s.p == pytest.approx(0.15, abs=1e-6)


def test_step_pool_holds_one_at_requirement(host):
    N = host.K.nutrients
    k = 0.047428
    s = _s(host)
    rec = _vitc(host)
    dtD = 1 / 1440
    for _ in range(1440):
        N.stepPool(s, rec, 90 * dtD, 90, k, dtD)
    # ZOH is exact at constant intake: Python doubles drift 0.0 over 1440 one-minute steps (the A0 impulse
    # form drifts 7.628e-7 per day)
    assert s.p == pytest.approx(1.0, abs=1e-12)


def test_step_pool_repletion(host):
    N = host.K.nutrients
    k = 0.047427999622147034
    rec = _rec(host, '{ kind = "pool", R = { 90, 75 }, k = 0.047428 }')
    s = _s(host, p=0.15)
    dtD = 1 / 1440
    a = 200 * dtD
    n = 0
    while s.p < 0.35:
        N.stepPool(s, rec, a, 90, k, dtD)
        n += 1
    # t = -math.log((0.35 - 200/90)/(0.15 - 200/90))/k = 2.139990935735342 d (briefing J 2.140; S0229)
    assert abs(n / 1440 - 2.139990935735342) <= 1 / 1440


def test_step_pool_cap(host):
    N = host.K.nutrients
    s = _s(host, p=0.99)
    N.stepPool(s, _vitc(host), 900, 90, 0.047428, 1 / 1440)
    assert s.p == 1.0
    # no pCap: the hoardable store passes 1
    s2 = _s(host, p=0.99)
    N.stepPool(s2, _rec(host, '{ kind = "pool" }'), 900, 90, 0.047428, 1 / 1440)
    assert s2.p > 1.0


def test_step_pool_degenerate(host):
    N = host.K.nutrients
    s = _s(host, p=0.5)
    assert N.stepPool(s, _vitc(host), 10, 90, 0.05, 0) == 0.5
    # a zero requirement never divides: the pool only decays
    s2 = _s(host, p=0.5)
    N.stepPool(s2, _vitc(host), 10, 0, 1.0, 1.0)
    assert s2.p == pytest.approx(0.5 * math.exp(-1.0), abs=TOL)


def test_step_zero_order(host):
    N = host.K.nutrients
    s = _s(host, p=0.5)
    assert N.stepZeroOrder(s, 0.1, 2.0) == pytest.approx(0.3, abs=TOL)
    assert N.stepZeroOrder(s, 0.1, 10.0) == 0


# -------------------------------------------------------------------------------------------------- grades


def test_grade(host):
    N = host.K.nutrients
    L = N.LADDER
    assert N.grade(0.8, L) == 1
    assert N.grade(0.70, L) == 2
    assert N.grade(0.45, L) == 3
    assert N.grade(0.25, L) == 4
    assert N.grade(0.0, L) == 4


def test_grade_hysteresis(host):
    N = host.K.nutrients
    L = N.LADDER
    assert N.gradeHyst(0.71, L, 2) == 2       # 0.71 <= 0.70 + 0.02
    assert N.gradeHyst(0.73, L, 2) == 1
    assert N.gradeHyst(0.71, L, 4) == 2       # up two rungs (0.71 > 0.45 + 0.02, > 0.25 + 0.02), not the third
    assert N.gradeHyst(0.26, L, 4) == 4       # 0.26 <= 0.27
    assert N.gradeHyst(0.30, L, 1) == 3       # worsening applies at once
    assert N.gradeHyst(0.80, L, 1) == 1


def test_grade_two(host):
    N = host.K.nutrients
    L = N.LADDER
    assert N.gradeTwo(0.9, 0.9, L, 1) == 1
    assert N.gradeTwo(0.9, 0.2, L, 1) == 4    # clinical on p2
    assert N.gradeTwo(0.1, 0.9, L, 1) == 3    # p alone stops at depleted
    assert N.gradeTwo(0.9, 0.26, L, 4) == 4   # leaving clinical needs p2 > 0.25 + 0.02
    assert N.gradeTwo(0.9, 0.28, L, 4) == 1


# -------------------------------------------------------------------------------------------------- excess


def _sel(host):
    return _rec(host, '{ kind = "excessOnly", ul = 400, chronic = { perDay = 7500, store = 7.2 } }')


def test_excess_e24_and_ul(host):
    N = host.K.nutrients
    s = _s(host)
    rec = _sel(host)
    assert N.excess(s, rec, 300, 1 / 1440, 80) == 0
    assert s.e24 == 300
    # 300 exp(-1/1440) + 150 = 449.79 >= 400
    assert N.excess(s, rec, 150, 1 / 1440, 80) == 1
    assert s.e24 == pytest.approx(300 * math.exp(-1 / 1440) + 150, abs=TOL)


def test_excess_chronic_hold(host):
    N = host.K.nutrients
    rec = _rec(host, '{ kind = "pool", chronic = { perDay = 7500 } }')
    s = _s(host)
    xs = []
    for _ in range(7):
        xs.append(N.excess(s, rec, 8000, 1.0, 80))
    # e24 >= 8000 > 7500 every day; ext reaches 7 on the seventh day
    assert xs == [0, 0, 0, 0, 0, 0, 2]
    assert s.ext == 7
    # zero intake: e24 (12644.3 after day 7) decays below 7500 on day 8 and the hold resets
    for _ in range(3):
        N.excess(s, rec, 0, 1.0, 80)
    assert s.ext == 0


def test_excess_store(host):
    N = host.K.nutrients
    rec = _sel(host)
    assert N.excess(_s(host, p=7.2), rec, 0, 1 / 1440, 80) == 2
    assert N.excess(_s(host, p=7.1), rec, 0, 1 / 1440, 80) == 0


def test_excess_acute_flag(host):
    N = host.K.nutrients
    rec = _sel(host)
    s = _s(host, ax=48, axr=3)
    assert N.excess(s, rec, 0, 1.0, 80) == 3       # 24 h of the 48 left
    assert s.ax == 24
    assert N.excess(s, rec, 0, 1.0, 80) == 0
    assert s.ax == 0
    assert N.excess(s, rec, 0, 1.0, 80) == 0       # floored at 0


def test_acute_test(host):
    N = host.K.nutrients
    iron = _rec(host, "{ acute = { perKg = { 20, 60 } } }")
    assert N.acuteTest(iron, 1600, 80, 0.5) == 2      # 20 mg/kg
    assert N.acuteTest(iron, 4800, 80, 0.5) == 3      # 60 mg/kg
    assert N.acuteTest(iron, 1100, 80, 0.1) == 2      # 13.75 x 1.5 = 20.625 on an empty stomach
    assert N.acuteTest(iron, 1100, 80, 0.5) == 0      # 13.75
    retinol = _rec(host, "{ acute = { abs = 90000 } }")
    assert N.acuteTest(retinol, 90000, 80, 0.5) == 2
    assert N.acuteTest(retinol, 89999, 80, 0.5) == 0
    assert N.acuteTest(_rec(host, "{ }"), 1e9, 80, 0.0) == 0


# -------------------------------------------------------------------------------------------------- minute


def _empty(host):
    return host.table({})


def test_minute_forty_days_zero_intake(host):
    N = host.K.nutrients
    recs = _records(host)
    st = N.newState(recs)
    ctx = _ctx(host)
    N.minute(st, recs, _empty(host), _empty(host), ctx, 60)
    assert st.allReplete is True
    for _ in range(40 * 24 - 1):
        N.minute(st, recs, _empty(host), _empty(host), ctx, 60)
    # Python doubles at k 0.047428: grade 2 at step 181, 3 at 405, 4 at 960 (p 0.1499999977)
    assert st.vitC.p == pytest.approx(0.14999999773287848, abs=1e-12)
    assert st.vitC.g == 4
    assert st.vitC.gl == 3
    assert st.vitC.ah == 0
    assert st.epoch == 3
    assert st.vitE.g == 1
    assert st.vitE.x == 0
    assert st.vitE.ah == 960
    assert st.allReplete is False
    assert st.ironGrade == 1
    assert st.anaemia is False
    assert st.vitDClinical is False


def test_minute_ledger_and_excess(host):
    N = host.K.nutrients
    recs = _records(host)
    st = N.newState(recs)
    absorbed = host.table(dict(vitC=0.0625, vitE=5))
    ingested = host.table(dict(vitC=2500, vitE=5))
    N.minute(st, recs, absorbed, ingested, _ctx(host, dial=10), 1)
    # the ledger: e24 only, p untouched
    assert st.vitE.e24 == 5
    assert st.vitE.p == 1
    # vitC: 2500 >= ul 2000 -> rung 1, one epoch; 0.0625 mg/min is R/1440 so p holds at 1
    assert st.vitC.x == 1
    assert st.vitC.p == pytest.approx(1.0, abs=1e-12)
    assert st.epoch == 1
    assert st.vitC.gl == 1


def test_minute_excess_off(host):
    N = host.K.nutrients
    recs = _records(host)
    st = N.newState(recs)
    ingested = host.table(dict(vitC=2500))
    N.minute(st, recs, _empty(host), ingested, _ctx(host, excessOn=False), 1)
    assert st.vitC.e24 == 2500       # the state still integrates
    assert st.vitC.x == 0
    assert st.vitE.x == 0
    assert st.epoch == 0


TWO = r"""
{
  ORDER = { "iron", "biotin", "copper", "selenium", "vitE", "water", "caffeine" },
  REC = {
    iron = { key = "iron", kind = "pool2", clinicalOnP2 = true, R = { 8, 18 }, ladder = { 0.70, 0.45, 0.25 } },
    biotin = { key = "biotin", kind = "counter", pCap = 1.0 },
    copper = { key = "copper", kind = "derived" },
    selenium = { key = "selenium", kind = "excessOnly", ul = 400 },
    vitE = { key = "vitE", kind = "ledger" },
    water = { key = "water", kind = "fast" },
    caffeine = { key = "caffeine", kind = "acute" },
  },
}
"""

STUB = r"""
function(key, s, rec, aAbs, ctx, dtD, dtH)
  STUB_CALLS[#STUB_CALLS + 1] = key
  if key == "iron" then
    s.p = 0.5
    s.p2 = 0.05
  end
  if key == "biotin" then
    s.p = 1.5
  end
end
"""


def test_minute_two_dispatch(host):
    N = host.K.nutrients
    recs = _records(host, TWO)
    st = N.newState(recs)
    host.G.STUB_CALLS = host.rt.table()
    ctx = _ctx(host)
    ctx.two = host.rt.eval(STUB)
    N.minute(st, recs, _empty(host), _empty(host), ctx, 1)
    calls = [host.G.STUB_CALLS[i] for i in range(1, len(host.G.STUB_CALLS) + 1)]
    assert calls == ["iron", "biotin", "copper", "selenium"]
    assert st.iron.g == 4                 # p 0.5 alone would be depleted; p2 0.05 is clinical
    assert st.biotin.p == 1.0             # the cap after ctx.two
    assert st.ironGrade == 4
    assert st.anaemia is True
    assert st.allReplete is False
    for key in ("vitE", "water", "caffeine", "selenium"):
        assert st[key].g == 1


def test_minute_without_two(host):
    N = host.K.nutrients
    recs = _records(host, TWO)
    st = N.newState(recs)
    st.iron.p = 0.5
    N.minute(st, recs, _empty(host), _empty(host), _ctx(host), 1)
    assert st.iron.g == 2                  # graded on p, p2 still 1
    assert st.ironGrade == 2
    assert st.anaemia is False


AGG = r"""
{
  ORDER = { "%s" },
  REC = { %s = { key = "%s", kind = "pool", R = { 1, 1 }, k = 0.05 } },
}
"""


@pytest.mark.parametrize("key,anaemia,vitd", [
    ("folate", True, False), ("vitB6", True, False), ("copper", True, False), ("vitD", False, True),
])
def test_minute_aggregates_clinical(host, key, anaemia, vitd):
    N = host.K.nutrients
    recs = _records(host, AGG % (key, key, key))
    st = N.newState(recs)
    st[key].p = 0.1
    N.minute(st, recs, _empty(host), _empty(host), _ctx(host), 1)
    assert st[key].g == 4
    assert st.anaemia is anaemia
    assert st.vitDClinical is vitd


def test_minute_b12_functional(host):
    N = host.K.nutrients
    recs = _records(host, AGG % ("vitB12", "vitB12", "vitB12"))
    st = N.newState(recs)
    N.minute(st, recs, _empty(host), _empty(host), _ctx(host), 1)
    assert st.anaemia is False
    st.vitB12.p2 = 0.5
    N.minute(st, recs, _empty(host), _empty(host), _ctx(host), 1)
    assert st.anaemia is True


def test_minute_creates_missing_key(host):
    N = host.K.nutrients
    recs = _records(host)
    st = N.newState(_records(host, '{ ORDER = { "vitC" }, REC = {} }'))
    assert st.vitE is None
    N.minute(st, recs, _empty(host), _empty(host), _ctx(host), 1)
    assert st.vitE.p == 1
    assert st.vitE.e24 == 0
