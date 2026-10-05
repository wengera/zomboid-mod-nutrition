"""The interaction factors and the non-pool steps (NR_Kernel_Interact.lua, K.interact), Plan 4 Task 10.

NR_Kernel_Interact.lua is a kernel file, so the session `host` fixture loads it through its glob; the real
records (NR_Data_Records.lua, Task 7) are loaded on top the way test_data_records.py does, and the iron,
vitamin A, B12, calcium, biotin, fibre, copper and selenium steps run against them. Every expectation was
recomputed in Python doubles before it was written (the expression sits beside it). One briefing hand value
was corrected in doubles: vitamin A from p 0.06 at i/R = 850/900 with the record's exact
k = ln(1/0.35)/120 = 0.008748517704155646 crosses 0.175 at 15.921663 d and 0.25 at 27.644402 d (formulas
briefing J's 16.008 d and 27.802 d match k ~ 0.0087, a rounded rate); both remain inside S0869's 6 weeks.
The phytate factor at 983 mg is exp(-0.00093 * 983) = 0.400841 (J: 0.400, S0536's 13.0/32.5).
"""
import math
import os
import pytest

TOL = 1e-9
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")


def _load(host, path):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@" + os.path.basename(path))()


@pytest.fixture(scope="module")
def rh(host):
    _load(host, os.path.join(SHARED, "NR_Data_Nutrients.lua"))
    _load(host, os.path.join(SHARED, "NR_Data_Records.lua"))
    return host


def _rec(h, key):
    return h.G.NutritionRevamp.data.records.REC[key]


def _ctx(h, **kw):
    base = {"sex": 1, "w": 80.0}
    base.update(kw)
    return h.table(base)


def _key(h):
    return h.K.nutrients.newKey()


def _iron_l0(h):
    # The real iron record with no basal loss, for the transfer-rate hand values.
    return h.rt.eval("""{ kind = "pool2", L = { 0, 0 },
        two = { totalPerKg = { 50, 40 }, storeShare = 0.25, hbShare = 2 / 3, xMax = 30, etaK = 0.5 } }""")


def _run(h, key, s, rec, aAbs, ctx, dtD, n):
    I = h.K.interact
    for _ in range(n):
        I.two(key, s, rec, aAbs, ctx, dtD, dtD * 24)


# ---- constants ----

def test_constants(host):
    I = host.K.interact
    assert (I.CA_FE_REF, I.CA_FE_MAX, I.PHY_SLOPE) == (300, 0.5, 0.00093)
    assert (I.B12_ACTIVE_FRAC, I.B12_ACTIVE_MAX, I.B12_PASSIVE, I.B12_PASSIVE_FROM) == (0.5, 2.0, 0.012, 4)
    assert (I.CAROTENE_OFF, I.RIBO_FE_GRADE, I.RIBO_FE_XFER, I.LAMBDA_ALC) == (1.0, 3, 0.5, 0.5)
    assert (I.CAF_MG_LOSS, I.CAF_LM_REF, I.ALC_MG_LOSS, I.BLOOD_FE, I.BIOTIN_DROP) == (0.02, 60, 2, 0.5, 0.31)


# ---- the factor functions ----

def test_calcium_iron(host):
    f = host.K.interact.calciumIron
    assert f(0) == 1
    assert f(300) == 0.5
    assert f(900) == 0.5
    assert abs(f(150) - 0.75) < TOL          # 1 - 0.5 * 150/300


def test_phytate_magnesium_and_zinc(host):
    I = host.K.interact
    assert abs(I.phytateMg(983) - 0.400) < 1e-3                 # S0536: 13.0/32.5 = 0.400
    assert abs(I.phytateMg(983) - 0.40084117598291386) < TOL     # exp(-0.00093 * 983)
    assert I.phytateMg(0) == 1
    assert I.phytateZn(983) == I.phytateMg(983)


def test_b12_ceiling(host):
    f = host.K.interact.b12Ceiling
    assert f(0) == 0
    assert f(1) == 0.5
    assert f(4) == 2.0
    assert abs(f(25) - 2.252) < TOL           # 2.0 + 0.012 * 21


def test_carotene_gate(host):
    f = host.K.interact.caroteneOn
    assert f(1.0) == 0
    assert f(0.5) == 1
    assert f(2.0) == 0
    assert f(0.5, 0.4) == 0                   # the record's caroteneOff, when passed, wins
    assert f(0.3, 0.4) == 1


def test_biotin_raw(host):
    f = host.K.interact.biotinRaw
    assert f(True) == 0
    assert f(False) == 1


def test_riboflavin_iron_transfer(host):
    f = host.K.interact.riboIronXfer
    assert [f(g) for g in (1, 2, 3, 4)] == [1, 1, 0.5, 0.5]


def test_thiamine_alcohol_rate(host):
    f = host.K.interact.thiamineAlcoholK
    assert f(0.05134423559703299, 0) == 0.05134423559703299
    assert abs(f(0.05134423559703299, 1.0) - 0.05134423559703299 * 1.5) < TOL


def test_caffeine_and_alcohol_losses(host):
    I = host.K.interact
    assert I.caffeineLossMg(200, 60) == (4.0, 4.0)       # 0.02 * 200 at the 60 kg reference
    mg, ca = I.caffeineLossMg(200, 30)
    assert abs(mg - 8.0) < TOL and abs(ca - 8.0) < TOL   # proportional to dose per lean mass, S0543
    assert I.alcoholLossMg(10) == 20                     # 2 mg per g


def test_zinc_copper_loss(host):
    f = host.K.interact.zincCopperLoss
    assert abs(f(80, 1, 0.02, 40) - 0.02) < TOL          # 0.02 * (80 - 40)/40 * 1
    assert f(30, 1, 0.02, 40) == 0
    assert f(40, 1, 0.02, 40) == 0


# ---- iron (A6) ----

def test_iron_initial_compartments(rh):
    I = rh.K.interact
    s = _key(rh)
    I.ironTwo(s, _rec(rh, "iron"), 0, 80.0, 1, 0, 1)
    assert s.S == 1000                                   # 0.25 * 50 * 80
    assert abs(s.H - 2666.6666666666665) < 1e-6          # 2/3 * 4000
    assert (s.p, s.p2) == (1, 1)
    f = _key(rh)
    I.ironTwo(f, _rec(rh, "iron"), 0, 60.0, 2, 0, 1)
    assert f.S == 600                                    # 0.25 * 40 * 60
    assert abs(f.H - 1600) < 1e-9


def test_iron_zero_intake_drains_the_store_in_1000_days(rh):
    s = _key(rh)
    ctx = _ctx(rh)
    _run(rh, "iron", s, _rec(rh, "iron"), 0, ctx, 1.0, 1000)
    H0 = 2 / 3 * 4000
    assert abs(s.S) < 1e-9                               # 1000 mg at 1.0 mg/d
    assert abs(s.H - H0) < 1e-9                          # held at H0 by the transfer
    assert abs(s.p) < 1e-12 and abs(s.p2 - 1) < 1e-12
    _run(rh, "iron", s, _rec(rh, "iron"), 0, ctx, 1.0, 1)
    assert s.S == 0
    assert abs(s.H - (H0 - 1)) < 1e-9
    assert s.p2 < 1


def test_iron_hb_deficit_refills_in_10_days_and_20_with_riboflavin_depleted(rh):
    rec = _iron_l0(rh)
    H0 = 2 / 3 * 4000
    for grade, steps in ((None, 240), (3, 480)):        # 300 mg at 30 mg/d (x 0.5) in 60-minute steps
        s = _key(rh)
        s.S = 500
        s.H = H0 - 300
        ctx = _ctx(rh) if grade is None else _ctx(rh, riboGrade=grade)
        _run(rh, "iron", s, rec, 0, ctx, 1 / 24, steps - 1)
        assert s.H < H0 - 1e-6
        _run(rh, "iron", s, rec, 0, ctx, 1 / 24, 1)
        assert abs(s.H - H0) < 1e-9
        assert abs(s.S - 200) < 1e-9
        assert abs(s.p2 - 1) < 1e-12 and abs(s.p - 0.2) < 1e-12


def test_iron_hb_deficit_with_the_basal_loss(rh):
    # The real L 1.0 mg/d nets 29 mg/d: 300/29 = 10.345 d, the 249th hourly step (300/(29/24) = 248.28).
    s = _key(rh)
    s.S = 500
    s.H = 2 / 3 * 4000 - 300
    _run(rh, "iron", s, _rec(rh, "iron"), 0, _ctx(rh), 1 / 24, 248)
    assert s.H < 2 / 3 * 4000 - 1e-6
    _run(rh, "iron", s, _rec(rh, "iron"), 0, _ctx(rh), 1 / 24, 1)
    assert abs(s.H - 2 / 3 * 4000) < 1e-9


def test_iron_store_absorption_eta(rh):
    I = rh.K.interact
    rec = _iron_l0(rh)
    for S, gain in ((0, 10.0), (500, 7.5), (1000, 5.0), (1500, 5.0)):   # eta = 1 - 0.5 clamp(S/1000, 0, 1)
        s = _key(rh)
        s.S = S
        s.H = 2 / 3 * 4000
        I.ironTwo(s, rec, 10, 80.0, 1, 1 / 1440, 1)
        assert abs(s.S - (S + gain)) < 1e-9
    assert abs(s.p - 1.505) < 1e-12                      # the store is uncapped: eta is its limit


def test_iron_bleed(rh):
    I = rh.K.interact
    s = _key(rh)
    assert I.ironBleed(s, 500) == 0                      # never stepped: no H yet
    I.ironTwo(s, _rec(rh, "iron"), 0, 80.0, 1, 0, 1)
    assert I.ironBleed(s, 500) == 250                    # 0.5 mg/mL
    assert abs(s.H - (2 / 3 * 4000 - 250)) < 1e-9
    assert abs(I.ironBleed(s, 1e9) - (2 / 3 * 4000 - 250)) < 1e-9
    assert s.H == 0


# ---- vitamin A ----

def test_vita_repletion_crossings(rh):
    k = math.log(1 / 0.35) / 120
    r = 850 / 900
    t175 = -math.log((r - 0.175) / (r - 0.06)) / k       # 15.921662673977865
    t25 = -math.log((r - 0.25) / (r - 0.06)) / k         # 27.644401518796847
    assert abs(t175 - 15.921662673977865) < 1e-9 and abs(t25 - 27.644401518796847) < 1e-9
    s = _key(rh)
    s.p = 0.06
    rec = _rec(rh, "vitA")
    ctx = _ctx(rh)
    dt = 1 / 24
    I = rh.K.interact
    cross = {}
    for n in range(1, 24 * 30 + 1):
        I.two("vitA", s, rec, 850 * dt, ctx, dt, 1)
        for thr in (0.175, 0.25):
            if thr not in cross and s.p >= thr:
                cross[thr] = n * dt
        if n == 1:
            assert abs(s.p2 - s.p / 0.175) < 1e-12       # plasma below the knee falls in proportion
    assert abs(cross[0.175] - t175) <= dt
    assert abs(cross[0.25] - t25) <= dt
    assert s.p2 == 1
    assert abs(s.p - (r + (0.06 - r) * math.exp(-k * 30))) < 1e-9   # ZOH is exact at constant intake


def test_vita_uncapped_and_dialled(rh):
    I = rh.K.interact
    rec = _rec(rh, "vitA")
    k = 0.008748517704155646
    s = _key(rh)
    I.two("vitA", s, rec, 2 * 900 * 10, _ctx(rh), 10, 240)          # i/R = 2 for 10 days
    assert abs(s.p - (2 + (1 - 2) * math.exp(-k * 10))) < 1e-12
    assert s.p > 1 and s.p2 == 1
    d = _key(rh)
    I.two("vitA", d, rec, 0, _ctx(rh, dial=10), 10, 240)            # dialExp 1: kEff = 10 k
    assert abs(d.p - math.exp(-k * 100)) < 1e-12
    f = _key(rh)
    I.two("vitA", f, rec, 700 * 1, _ctx(rh, sex=2), 1, 24)          # female R 700: i = R holds p
    assert abs(f.p - 1) < 1e-12


# ---- B12 ----

def test_b12_zero_intake_to_the_threshold_and_damage(rh):
    s = _key(rh)
    rec = _rec(rh, "vitB12")
    ctx = _ctx(rh)
    _run(rh, "vitB12", s, rec, 0, ctx, 1.0, 2302)        # ln(10)/0.001 = 2302.585 d
    assert abs(s.p - math.exp(-2.302)) < 1e-9
    assert s.p > 0.10 and s.p2 == 1 and s.dmg == 0
    _run(rh, "vitB12", s, rec, 0, ctx, 1.0, 1)
    assert s.p < 0.10 and s.p2 < 1
    assert s.dmg == 24                                   # one day below the threshold, in hours
    _run(rh, "vitB12", s, rec, 24 * 1000, ctx, 1000, 1)  # i/R 10: repletion clears the deficit, never the damage
    assert s.p == 1 and s.p2 == 1                        # capped at pCap 1
    assert s.dmg == 24


# ---- the counters, the derived copper and the unstepped kinds ----

def test_calcium_bone_counter(rh):
    I = rh.K.interact
    rec = _rec(rh, "calcium")
    full = 1400 * 1000
    s = _key(rh)
    I.two("calcium", s, rec, 0, _ctx(rh), 1.0, 24)
    assert s.bone == full - 200                          # 200 mg/d obligatory loss, S0414
    assert abs(s.p - (full - 200) / full) < 1e-15
    s.bone = full - 1000
    I.two("calcium", s, rec, 250, _ctx(rh), 1 / 1440, 1 / 60)    # a 1000 mg meal absorbed at 0.25 upstream
    assert abs(s.bone - (full - 1000 + 250 - 200 / 1440)) < 1e-9
    I.two("calcium", s, rec, 5000, _ctx(rh), 1 / 1440, 1 / 60)
    assert s.bone == full and s.p == 1                   # held at the starting skeleton
    f = _key(rh)
    I.two("calcium", f, rec, 0, _ctx(rh, sex=2), 1.0, 24)
    assert f.bone == 1200 * 1000 - 200
    f.bone = 10
    I.two("calcium", f, rec, 0, _ctx(rh, sex=2), 1.0, 24)
    assert f.bone == 0 and f.p == 0


def test_biotin_raw_egg_counter(rh):
    rec = _rec(rh, "biotin")
    s = _key(rh)
    _run(rh, "biotin", s, rec, 0, _ctx(rh, rawEggDay=True), 1.0, 45)
    assert s.ext == 45 and abs(s.p - (1 - 0.5 * 0.31)) < 1e-12
    _run(rh, "biotin", s, rec, 0, _ctx(rh, rawEggDay=True), 1.0, 45)
    assert s.ext == 90 and abs(s.p - 0.69) < 1e-12       # the cosmetic rung at cosmeticDays
    _run(rh, "biotin", s, rec, 0, _ctx(rh, rawEggDay=True), 1.0, 10)
    assert abs(s.p - 0.69) < 1e-12                       # clamped past cosmeticDays
    assert rh.K.nutrients.grade(s.p, rh.K.nutrients.LADDER) == 2
    _run(rh, "biotin", s, rec, 0, _ctx(rh), 1.0, 99)     # rawEggDay nil: recovering
    assert s.ext == 1
    _run(rh, "biotin", s, rec, 0, _ctx(rh, rawEggDay=False), 1.0, 2)
    assert s.ext == 0 and s.p == 1


def test_fibre_ema(rh):
    rec = _rec(rh, "fibre")
    s = _key(rh)
    _run(rh, "fibre", s, rec, 38 / 24, _ctx(rh), 1 / 24, 48)     # intake at R holds p = 1
    assert abs(s.p - 1) < 1e-12
    _run(rh, "fibre", s, rec, 0, _ctx(rh), 1 / 24, 84)           # 3.5 d at zero: the half-life
    assert abs(s.p - 0.5) < 1e-12
    f = _key(rh)
    _run(rh, "fibre", f, rec, 25 * 2, _ctx(rh, sex=2), 2.0, 50)  # female R 25: at R holds p
    assert abs(f.p - 1) < 1e-12


def test_copper_under_zinc_excess(rh):
    rec = _rec(rh, "copper")
    s = _key(rh)
    _run(rh, "copper", s, rec, 0, _ctx(rh, e24Zn=80), 1 / 24, 30 * 24)
    assert abs(s.p - 0.5486743740814882) < 1e-9          # hourly Euler; continuous exp(-0.6) = 0.548812
    _run(rh, "copper", s, rec, 0, _ctx(rh), 1 / 24, 24 * 2000)   # e24Zn nil reads 0: recovers to 1
    assert abs(s.p - 1) < 1e-9 and s.p <= 1
    _run(rh, "copper", s, rec, 0, _ctx(rh, e24Zn=1e9), 1, 1)
    assert s.p == 0                                      # floored


def test_copper_capped_at_one(rh):
    rec = _rec(rh, "copper")
    s = _key(rh)
    s.p = 0.999
    rh.K.interact.two("copper", s, rec, 0, _ctx(rh), 100, 2400)
    assert s.p == 1


def test_unstepped_kinds_and_keys(rh):
    I = rh.K.interact
    sel = _key(rh)
    I.two("selenium", sel, _rec(rh, "selenium"), 500, _ctx(rh), 1, 24)
    assert (sel.p, sel.p2) == (1, 1)
    for kind in ("pool2", "counter", "derived", "weird"):
        s = _key(rh)
        rec = rh.rt.eval('{ kind = "%s" }' % kind)
        I.two("zzz", s, rec, 500, _ctx(rh), 1, 24)
        assert rh.py(s) == rh.py(_key(rh))
    z = _key(rh)
    I.two("iron", z, _rec(rh, "iron"), 500, _ctx(rh), 0, 0)     # a zero step is a no-op
    assert z.S is None and z.p == 1


# ---- through the engine ----

def test_engine_runs_the_real_records_through_two(rh):
    N = rh.K.nutrients
    recs = rh.G.NutritionRevamp.data.records
    state = N.newState(recs)
    ctx = rh.table({"sex": 1, "w": 80.0, "eeMJ": 10.0, "pDay": 80.0})
    ctx.two = rh.K.interact.two
    empty = rh.table({})
    for _ in range(30 * 24):
        N.minute(state, recs, empty, empty, ctx, 60)
    iron = state.iron
    assert abs(iron.S - (1000 - 30)) < 1e-6 and abs(iron.p - 0.97) < 1e-9 and abs(iron.p2 - 1) < 1e-9
    assert iron.g == 1
    assert abs(state.vitA.p - math.exp(-0.008748517704155646 * 30)) < 1e-9 and state.vitA.p2 == 1
    assert abs(state.vitB12.p - math.exp(-0.03)) < 1e-9 and state.vitB12.p2 == 1 and state.vitB12.dmg == 0
    assert abs(state.calcium.bone - (1400000 - 6000)) < 1e-6 and state.calcium.g == 1
    assert state.biotin.p == 1 and state.copper.p == 1 and state.selenium.p == 1
    assert abs(state.fibre.p - math.exp(-math.log(2) / 3.5 * 30)) < 1e-9
    assert state.fibre.g == 3                            # below 0.25, above the 0.0 clinical rung
    assert state.epoch > 0
