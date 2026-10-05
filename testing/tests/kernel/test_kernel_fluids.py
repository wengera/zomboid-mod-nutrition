"""Water, the electrolytes and the thirst view (NR_Kernel_Fluids.lua), Plan 4 Task 8.

NR_Kernel_Fluids.lua is a kernel file (its name is NR_Kernel*), so the session `host` fixture loads it
through its glob and already has NutritionRevamp.kernel.fluids. Every expectation below was recomputed in
Python doubles from the file's constants before it was written (the expression sits in the comment beside
it): total body water 0.73 x lean mass (open S1091); the osmotic reference 140 mmol/L, the midpoint of
S1045's 135-145 normal range; the Edelman form (open S1092); basal turnover = the water AI 3700/2700 g/d
(S0088; open S1093); sweat 1.0 L/h x clamp((MET - 3)/5, 0, 1.5) x thermoFluids x sweatK (S0090/S0091; open
S1094); cold diuresis 0.1 L/h (open S1053); alcohol diuresis 4 g/g x (1 - 0.45 clamp(d/2, 0, 1)) (S0521-
S0523; the 2 % knee open S1095); surplus clearance 320 g/h (S0521); the renal tau 24 h (open S1096/S1097);
the thirst knots (#0509, S0092, S0709; open S1098), the osmotic term and the hypotonic cap (S0102; open
S1099), the kill cap 0.83 (ruling 8); the hyponatraemia ladder 135/120/112 (S0102/S1047); and ruling T1-1's
thirst view over the pool plus the stomach's pending water.
"""
import pytest

TOL = 1e-9


def _close(a, b, tol=TOL):
    return abs(a - b) < tol


def _new(host, lm=65.6, sweatK=1.0, naSweat=37.0):
    return host.K.fluids.new(lm, sweatK, naSweat)


def _ctx(host, **kw):
    c = dict(sex=1, met=1.0, thermoFluids=1.0, coldMult=1.0, ethanolAbsG=0.0, dehydPct=0.0)
    c.update(kw)
    return host.table(c)


def test_constants(host):
    F = host.K.fluids
    assert (F.FV, F.TBW_PER_LM, F.OSM_REF) == (1, 0.73, 140)
    assert list(host.py(F.AI).values()) == [3700, 2700]
    assert (F.SWEAT_LH, F.SWEAT_MET_LO, F.SWEAT_MET_HI, F.SWEAT_CAP) == (1.0, 3, 8, 1.5)
    assert list(host.py(F.SWEATK_RANGE).values()) == [0.5, 1.5]
    assert F.NA_SWEAT_MEAN == 37
    assert list(host.py(F.NA_SWEAT_RANGE).values()) == [10, 90]
    assert (F.K_SWEAT, F.COLD_DIURESIS_LH, F.ALC_DIURESIS_G_PER_G, F.ALC_HYPO_K, F.ALC_KNEE_PCT) == (5, 0.1, 4, 0.45, 2)
    assert (F.CLEAR_GH, F.NA_TAU_H, F.K_TAU_H) == (320, 24, 24)
    assert (F.NA_MG_PER_MMOL, F.K_MG_PER_MMOL) == (23, 39.1)
    knots = [list(host.py(k).values()) for k in host.py(F.THIRST_KNOTS).values()]
    assert knots == [[0, 0], [1, 0.12], [2, 0.25], [4, 0.70], [6, 0.84], [8, 1.0]]
    assert (F.OSM_SLOPE, F.OSM_GAIN, F.OSM_MAX, F.HYPO_NA, F.HYPO_CAP, F.KILL_CAP) == (0.03, 0.25, 4, 135, 0.11, 0.83)
    assert list(host.py(F.HYPONAT).values()) == [135, 120, 112]
    assert (F.SWEAT_ACTIVE_SHARE, F.EMA_MIN, F.SEVERE_DEHYD_PCT) == (0.5, 360, 10)


def test_new_state_shape(host):
    f = host.py(_new(host, 65.6, 1.2, 50))
    assert f == dict(fv=1, water=0, na=0, k=0, sweatK=1.2, naSweat=50, sweat6h=0, loss6h=0, dehydPct=0, c=1,
                     naPlasma=140, thirstTarget=0, autoDrop=0, sweatLmin=0)


def test_new_defaults_the_draws(host):
    f = host.K.fluids.new(65.6, None, None)
    assert f.sweatK == 1 and f.naSweat == 37


def test_tbw0_and_osm_pool(host):
    assert _close(host.K.fluids.tbw0(65.6), 47.888)  # 0.73*65.6
    assert _close(host.K.fluids.osmPool0(65.6), 6704.32)  # 140*47.888


def test_intake_converts_mg_to_mmol(host):
    F = host.K.fluids
    f = _new(host)
    F.intake(f, host.table(dict(water=500.0, sodium=230.0, potassium=391.0)))
    assert _close(f.water, 500) and _close(f.na, 10) and _close(f.k, 10)  # 230/23, 391/39.1
    F.intake(f, host.table(dict()))  # every key missing reads 0
    assert _close(f.water, 500) and _close(f.na, 10) and _close(f.k, 10)


def test_water_intoxication_cross_check(host):
    # S1046: ~8 L in 3 h with 0.96 L cleared -> Na 120; c = 47.888/(47.888 + 7.04) = 0.8718322167200699
    F = host.K.fluids
    f = _new(host)
    f.water = 8000 - 960
    c = F.conc(f, 65.6)
    assert _close(c, 0.8718322167200699)
    assert _close(F.naPlasma(c), 122.0565103408098)  # 140*c
    assert abs(F.naPlasma(c) - 122.1) < 1e-1


def test_conc_neutral_and_solute(host):
    F = host.K.fluids
    f = _new(host)
    assert _close(F.conc(f, 65.6), 1.0)
    f.na = 6704.32 * 0.03  # +3 % of the osmotic pool -> c 1.03
    assert _close(F.conc(f, 65.6), 1.03)


def test_conc_denominator_guard(host):
    # tbw0 + water/1000 = 47.888 - 45 = 2.888 < 0.1*47.888 -> the denominator is 4.7888 and c = 10
    F = host.K.fluids
    f = _new(host)
    f.water = -45000
    assert _close(F.conc(f, 65.6), 10.0)


def test_thirst_knots(host):
    T = host.K.fluids.thirstTarget
    assert _close(T(2, 1, 140, True), 0.25)
    assert _close(T(1, 1, 140, True), 0.12)
    assert _close(T(3, 1, 140, True), 0.475)  # 0.25 + 0.45*(3 - 2)/2
    assert _close(T(0, 1, 140, True), 0.0)
    assert _close(T(8, 1, 140, True), 1.0)
    assert _close(T(9, 1, 140, True), 1.0)  # above the top knot
    assert _close(T(7, 1, 140, True), 0.92)  # 0.84 + 0.16*(7 - 6)/2


def test_thirst_osmotic_term(host):
    T = host.K.fluids.thirstTarget
    assert _close(T(0, 1.03, 144.2, True), 0.25)  # 0.25*((1.03 - 1)/0.03) = 0.2500000000000002
    assert _close(T(2, 1.03, 144.2, True), 0.4375)  # 1 - 0.75*0.75
    assert _close(T(0, 1.20, 168, True), 1.0)  # tOsm clamped at 4 x 0.25, then min 1


def test_thirst_caps(host):
    T = host.K.fluids.thirstTarget
    assert _close(T(8, 1, 140, False), 0.83)  # the kill cap, ruling 8
    assert _close(T(2, 1, 140, False), 0.25)  # under the kill cap: unchanged
    assert _close(T(2, 1, 130, True), 0.11)  # hypotonic: capped, S0102
    assert _close(T(0.5, 1, 130, True), 0.06)  # 0.12*0.5 is under the hypotonic cap


def test_basal_ten_hours_at_rest(host):
    # -3700*600/1440 = -1541.6666666666506; dehydPct = 100*1.5416666/80 = 1.9270833333333133
    F = host.K.fluids
    f = _new(host)
    ctx = _ctx(host)
    for _ in range(600):
        assert F.losses(f, ctx, 1) == 0
    assert _close(f.water, -1541.6666666666506, 1e-6)
    assert _close(f.na, 0) and _close(f.k, 0)
    assert _close(F.dehydPct(f, 80), 1.9270833333333133, 1e-8)
    assert _close(F.dehydPct(f, 80, 0), 1.9270833333333133, 1e-8)
    # ruling T1-1: the thirst view reads the pool plus 1 L still in the stomach: 100*0.5416666/80
    assert _close(F.dehydPct(f, 80, 1000), 0.6770833333333133, 1e-8)
    assert _close(F.dehydPct(f, 80, 5000), 0.0)  # a net surplus reads 0
    f2 = _new(host)
    F.losses(f2, _ctx(host, sex=2), 1440)
    assert _close(f2.water, -2700)  # the female AI over a day


def test_sweat_rate(host):
    S = host.K.fluids.sweatLh
    assert _close(S(8, 1, 1), 1.0)  # 1.0*clamp(5/5, 0, 1.5)
    assert _close(S(1, 1, 1), 0.0)
    assert _close(S(20, 1, 1), 1.5)  # the cap
    assert _close(S(5.5, 2, 0.5), 0.5)  # 1.0*0.5*2*0.5


def test_sweat_losses_one_minute(host):
    # met 8: 1.0 L/h -> 1/60 L this minute; water -(1000/60 + 3700/1440); na -(1/60)*37; k -(1/60)*5
    F = host.K.fluids
    f = _new(host)
    L = F.losses(f, _ctx(host, met=8.0), 1)
    assert _close(L, 1 / 60)
    assert _close(f.sweatLmin, 1 / 60)
    assert _close(f.water, -(1000 / 60 + 3700 / 1440))
    assert _close(f.na, -(1 / 60) * 37)
    assert _close(f.k, -(1 / 60) * 5)


def test_cold_diuresis(host):
    # 0.1 L/h x clamp(2 - 1, 0, 1) x 1000/60 = 1.6666666666666667 g in a minute beyond basal
    F = host.K.fluids
    f = _new(host)
    F.losses(f, _ctx(host, coldMult=2.0), 1)
    assert _close(f.water, -(1.6666666666666667 + 3700 / 1440))


def test_alcohol_diuresis(host):
    # 4*31.6 = 126.4 g euhydrated; x (1 - 0.45) = 69.52000000000001 g at dehydPct 2
    F = host.K.fluids
    f = _new(host)
    F.losses(f, _ctx(host, ethanolAbsG=31.6), 1)
    assert _close(-f.water - 3700 / 1440, 126.4)
    f = _new(host)
    F.losses(f, _ctx(host, ethanolAbsG=31.6, dehydPct=2.0), 1)
    assert _close(-f.water - 3700 / 1440, 69.52000000000001)
    assert _close(69.52000000000001 / 126.4, 0.55)


def test_clearance_one_hour(host):
    # 1000 g surplus cleared at 320/60 g per minute for 60 minutes -> 679.9999999999977
    F = host.K.fluids
    f = _new(host)
    f.water = 1000
    f.na = 100
    f.k = 100
    for _ in range(60):
        F.clearance(f, 1)
    assert _close(f.water, 680, 1e-8)
    assert _close(f.na, 95.91755736193709, 1e-8)  # 100*(1 - 1/1440)^60
    assert _close(f.k, 95.91755736193709, 1e-8)


def test_clearance_keeps_a_deficit(host):
    F = host.K.fluids
    f = _new(host)
    f.water = -500
    f.na = -20
    f.k = -5
    F.clearance(f, 60)
    assert (f.water, f.na, f.k) == (-500, -20, -5)
    f.water = 100
    F.clearance(f, 60)
    assert _close(f.water, 0)  # a surplus under the hour's cap is cleared to 0, never past it


def test_hyponat_grade(host):
    G = host.K.fluids.hyponatGrade
    assert G(140) == 0 and G(135) == 0
    assert G(130) == 1 and G(120) == 1
    assert G(118) == 2 and G(112) == 2
    assert G(110) == 3


def test_sweat_active(host):
    # 360 rested minutes: sweat6h 0, loss6h 1.6255130210771078 -> inactive; then 60 minutes at met 8:
    # sweat6h 2.56190934683809, loss6h 4.332518372093135, share 0.5913210578263226 > 0.5 -> active
    F = host.K.fluids
    f = _new(host)
    assert F.sweatActive(f) is False  # no loss yet: loss6h 0
    rest = _ctx(host)
    for _ in range(360):
        F.losses(f, rest, 1)
    assert _close(f.sweat6h, 0.0) and _close(f.loss6h, 1.6255130210771078, 1e-9)
    assert F.sweatActive(f) is False
    work = _ctx(host, met=8.0)
    for _ in range(60):
        F.losses(f, work, 1)
    assert _close(f.sweat6h, 2.56190934683809, 1e-9)
    assert _close(f.loss6h, 4.332518372093135, 1e-9)
    assert F.sweatActive(f) is True


def test_ema_alpha_capped_on_a_long_step(host):
    # a step longer than 6 h sets the EMAs to the step's per-minute sample (alpha capped at 1)
    F = host.K.fluids
    f = _new(host)
    F.losses(f, _ctx(host), 720)
    assert _close(f.loss6h, 3700 / 1440)
    assert _close(f.sweat6h, 0.0)
