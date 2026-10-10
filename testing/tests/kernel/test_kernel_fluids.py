"""Water, the electrolytes and the thirst view (NR_Kernel_Fluids.lua), Plan 4 Task 8.

NR_Kernel_Fluids.lua is a kernel file (its name is NR_Kernel*), so the session `host` fixture loads it
through its glob and already has NutritionRevamp.kernel.fluids. Every expectation below was recomputed in
Python doubles from the file's constants before it was written (the expression sits in the comment beside
it): total body water 0.73 x lean mass (open S1091); the osmotic reference 140 mmol/L, the midpoint of
S1045's 135-145 normal range; the Edelman form (open S1092); basal turnover = the water AI 3700/2700 g/d
(S0088; open S1093); sweat 1.0 L/h x clamp((MET - 3)/5, 0, 1.5) x thermoFluids x sweatK (S0090/S0091; open
S1094); cold diuresis 0.1 L/h (open S1053); alcohol diuresis 4 g/g x (1 - 0.45 clamp(d/2, 0, 1)) (S0521-
S0523; the 2 % knee open S1095); the clearance of water above the set point at 672 g/h (S1685); the sodium
tau 33.8 h (S1670) and the potassium tau 24 h (open S1097); the obligatory sodium loss 8 mmol/d (S1665); the
set point weu = 1000/140 g per mmol of na + k (S1683; Plan 11f Task 5b); the thirst knots (#0509, S0092,
S0709; open S1098), the osmotic term (open S1099) and the hypotonic cap 0.09 under autoDrink's 0.1 (#2770;
open S1695), the kill cap 0.83 (ruling 8); the hyponatraemia ladder 135/120/112 (S0102/S1047); and ruling
T1-1's thirst view over the pool plus the stomach's pending water.
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
    assert (F.TBW_PER_LM, F.OSM_REF) == (0.73, 140)
    assert list(host.py(F.AI).values()) == [3700, 2700]
    assert (F.SWEAT_LH, F.SWEAT_MET_LO, F.SWEAT_MET_HI, F.SWEAT_CAP) == (1.0, 3, 8, 1.5)
    assert list(host.py(F.SWEATK_RANGE).values()) == [0.5, 1.5]
    assert F.NA_SWEAT_MEAN == 37
    assert list(host.py(F.NA_SWEAT_RANGE).values()) == [10, 90]
    assert (F.K_SWEAT, F.COLD_DIURESIS_LH, F.ALC_DIURESIS_G_PER_G, F.ALC_HYPO_K, F.ALC_KNEE_PCT) == (5, 0.1, 4, 0.45, 2)
    assert (F.CLEAR_GH, F.NA_TAU_H, F.K_TAU_H) == (672, 33.8, 24)
    assert F.BASAL_NA == 8 and F.WATER_PER_MMOL == 1000 / 140
    assert (F.NA_MG_PER_MMOL, F.K_MG_PER_MMOL) == (23, 39.1)
    knots = [list(host.py(k).values()) for k in host.py(F.THIRST_KNOTS).values()]
    assert knots == [[0, 0], [1, 0.12], [2, 0.25], [4, 0.70], [6, 0.84], [8, 1.0]]
    assert (F.OSM_SLOPE, F.OSM_GAIN, F.OSM_MAX, F.HYPO_NA, F.HYPO_CAP, F.KILL_CAP) == (0.03, 0.25, 4, 135, 0.09, 0.83)
    assert list(host.py(F.HYPONAT).values()) == [135, 120, 112]
    assert (F.SWEAT_ACTIVE_SHARE, F.EMA_MIN, F.SEVERE_DEHYD_PCT) == (0.5, 360, 10)


def test_new_state_shape(host):
    f = host.py(_new(host, 65.6, 1.2, 50))
    assert f == dict(water=0, na=0, k=0, sweatK=1.2, naSweat=50, sweat6h=0, loss6h=0, dehydPct=0, c=1,
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
    assert _close(T(2, 1, 130, True), 0.09)  # hypotonic: capped under autoDrink's 0.1 trigger (#2770)
    assert _close(T(0.5, 1, 130, True), 0.06)  # 0.12*0.5 is under the hypotonic cap


def test_basal_ten_hours_at_rest(host):
    # -3700*600/1440 = -1541.6666666666506 g of water
    F = host.K.fluids
    f = _new(host)
    ctx = _ctx(host)
    for _ in range(600):
        assert F.losses(f, ctx, 1) == 0
    assert _close(f.water, -1541.6666666666506, 1e-6)
    # Plan 11f Task 5b: the basal loss carries S1665's obligatory 8 mmol/d, not ruling T11-3's isotonic 0.65 share
    # (336.7 mmol/d, finding F-T5-1): -8*600/1440 = -3.3333333333333335
    assert _close(f.na, -3.3333333333333335, 1e-9) and _close(f.k, 0)
    # the deficit against the set point weu = 1000/140 * na = -23.80952380952381 g:
    # 100*(1541.6666666666667 - 23.80952380952381)/1000/80 = 1.8973214285714284
    assert _close(F.weu(f, 80), 1000 / 140 * -3.3333333333333335, 1e-9)
    assert _close(F.dehydPct(f, 80), 1.8973214285714284, 1e-8)
    c = F.conc(f, 65.6)
    p0 = 140 * 0.73 * 65.6
    t0 = 0.73 * 65.6
    assert _close(c, (p0 + f.na) / p0 * t0 / (t0 - 1.5416666666666506), 1e-9)
    assert _close(c, 1.0327503177422985, 1e-6)
    assert _close(F.naPlasma(c), 140 * c, 1e-9)
    want = F.thirstTarget(1.8973214285714284, c, 140 * c, True)
    tvol = 0.12 + 0.13 * 0.8973214285714284
    tosm = 0.25 * ((c - 1) / 0.03)
    assert _close(want, 1 - (1 - tvol) * (1 - tosm), 1e-9)
    # T11-3's motive re-priced: 10 h dry at rest reads 0.445 (it read 0.314 under the 0.65 share); reported against
    # Thompson 1986's osmotic thirst slope (S1689), never tuned
    assert _close(want, 0.4449842570965634, 1e-6)
    assert _close(F.dehydPct(f, 80, 0), 1.8973214285714284, 1e-8)
    # ruling T1-1: the thirst view reads the pool plus 1 L still in the stomach: 100*0.5178571/80
    assert _close(F.dehydPct(f, 80, 1000), 0.6473214285714286, 1e-8)
    assert _close(F.dehydPct(f, 80, 5000), 0.0)  # a net surplus reads 0
    f2 = _new(host)
    F.losses(f2, _ctx(host, sex=2), 1440)
    assert _close(f2.water, -2700)  # the female AI over a day


def test_sweat_sodium_draw(host):
    # 10 + 80 r^2 has mean 36.7 and range 10-90 (S0518; ruling T11-4)
    D = host.K.fluids.naSweatOf
    assert _close(D(0.5), 30.0)
    assert _close(D(0), 10.0)
    assert _close(D(1), 90.0)
    assert _close(D((27 / 80) ** 0.5), 37.0)


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
    assert _close(f.na, -(1 / 60) * 37 - 8 / 1440)  # sweat sodium plus S1665's obligatory loss
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
    # 1000 g above a zero set point cleared at 672/60 g per minute for 60 minutes -> 328 (S1685)
    F = host.K.fluids
    f = _new(host)
    f.water = 1000
    for _ in range(60):
        F.clearance(f, 1, 80)
    assert _close(f.water, 328, 1e-8)
    # the surpluses first-order: na at tau 33.8 h, k at 24 h; 5000 g of water clears its hour's 672
    f = _new(host)
    f.water = 5000
    f.na = 100
    f.k = 100
    for _ in range(60):
        F.clearance(f, 1, 80)
    assert _close(f.na, 97.08404925098363, 1e-8)  # 100*(1 - 1/(60*33.8))^60
    assert _close(f.k, 95.91755736193707, 1e-8)  # 100*(1 - 1/1440)^60
    assert _close(f.water, 4328, 1e-8)


def test_clearance_holds_the_water_a_sodium_surplus_carries(host):
    # water follows sodium: 1000 g against a set point of 1000/140*(na + k), about 1400 g, is no surplus
    F = host.K.fluids
    f = _new(host)
    f.water = 1000
    f.na = 100
    f.k = 100
    F.clearance(f, 60, 80)
    assert _close(f.water, 1000)
    assert F.weu(f, 80) > 1000
    assert F.dehydPct(f, 80) > 0  # below its set point: a deficit, though the pool holds a litre


def test_clearance_keeps_a_deficit(host):
    F = host.K.fluids
    f = _new(host)
    f.water = -500
    f.na = -20
    f.k = -5
    F.clearance(f, 60, 80)
    assert (f.water, f.na, f.k) == (-500, -20, -5)
    f.water = 100
    F.clearance(f, 60, 80)
    assert _close(f.water, -178.57142857142858)  # a surplus under the hour's cap is cleared to weu, never past it


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


def test_conc_counts_extra_water_as_if_in_the_pool(host):
    # Plan 11f Task 5b fix 1: the thirst view's c counts the swallowed water (S1698, S1699); a nil extraG reads 0
    F = host.K.fluids
    f = _new(host)
    f.na = 100
    f.water = -1500
    view = F.conc(f, 65.6, 1000)
    f.water = -500
    assert _close(view, F.conc(f, 65.6))
    f.water = -1500
    assert _close(F.conc(f, 65.6, None), F.conc(f, 65.6))
    assert view < F.conc(f, 65.6)


def test_the_set_point_follows_sodium_to_the_volume_defence_onset(host):
    # Plan 11f Task 5b fix 1 (review finding 1): ECF 0.20 L/kg (S1714: 14 L in the 70 kg man), 16000 g at 80 kg; water
    # follows na + k isotonically (S1683) up to 8 % of it, 1280 g = 179.2 mmol (S1717, S1722: an 8-10 % volume fall;
    # applied to ECF, a game choice); past it the following weight falls linearly to 0 at full defence, 20 % of ECF
    # (S1729, McCance Fig. 1 by eye), so the contraction is b - (b - a) exp(-(x - a)/(b - a)) for a requested x
    F = host.K.fluids
    assert (F.ECF_PER_KG, F.DEFEND_ONSET, F.DEFEND_FULL) == (0.2, 0.08, 0.2)
    f = _new(host)
    f.na = -150
    f.k = -20
    assert _close(F.weu(f, 80), 1000 / 140 * -170)
    f.k = 0
    for na, want in ((-300, -1975.025014075266), (-1000, -3109.395032863671), (-5000, -3199.999968779741)):
        f.na = na
        assert _close(F.weu(f, 80), want, 1e-6), na
    # continuous at the onset, monotone, never past full defence
    f.na = -179.2 + 1e-7
    lo = F.weu(f, 80)
    f.na = -179.2 - 1e-7
    assert abs(F.weu(f, 80) - lo) < 1e-5
    prev = 0
    for i in range(1, 400):
        f.na = -5.0 * i
        v = F.weu(f, 80)
        assert -3200 < v < prev, i
        prev = v
    # the bound scales with the body; a surplus is never bounded
    f.na = -5000
    assert _close(F.weu(f, 60), -0.2 * 0.2 * 60 * 1000, 1e-3)
    f.na = 5000
    assert _close(F.weu(f, 80), 1000 / 140 * 5000)


def test_past_the_bound_a_sodium_deficit_reads_as_dehydration(host):
    # the set point held at -3109.4 g by a 1000 mmol deficit: water below it is a deficit, water above it clears
    F = host.K.fluids
    f = _new(host)
    f.na = -1000
    f.water = -3109.395032863671
    assert F.dehydPct(f, 80) < 1e-9
    f.water = -5000
    assert _close(F.dehydPct(f, 80), 100 * (5000 - 3109.395032863671) / 1000 / 80, 1e-6)
    f.water = -2000
    F.clearance(f, 60, 80)
    assert _close(f.water, -2672, 1e-6)  # an hour at 672 g/h toward the bounded set point (S1685)
    assert f.na == -1000  # a deficit is conserved


def test_clearance_reads_the_water_against_the_set_point_the_surplus_step_leaves(host):
    # the order (Plan 11f Task 5b): na and k clear first, then the water above the NEW set point; a step that cleared
    # the water against the old one (mutation M1) leaves the hour's water at the old set point, above the new
    F = host.K.fluids
    f = _new(host)
    f.na = 1000
    f.water = F.weu(f, 80)
    F.clearance(f, 60, 80)
    assert _close(f.na, 1000 * (1 - 1 / 33.8))
    assert _close(f.water, F.weu(f, 80), 1e-6)
    assert f.water < 1000 / 140 * 1000 - 200


def test_the_volume_defence_relaxes_the_hypotonic_cap(host):
    # Plan 11f Task 5b fix 2 (review finding 1, candidate C-9): past the onset a volume-thirst term relaxes the
    # hypotonic cap toward ordinary thirst by the defence weight, the set point's own ramp (x - a)/(b - a) on the
    # contraction reached x = -weu, so a salt-depleted body drinks and dilutes (S1729: volume "relatively well
    # maintained ... at the expense of the osmotic pressure"; S1731: the subjects drank freely; S1724: volume thirst)
    F = host.K.fluids
    T = F.thirstTarget
    f = _new(host)
    # inside the onset (1280 g = 179.2 mmol at 80 kg) there is no defence: the cap holds as before
    for na in (500.0, 0.0, -100.0, -179.2 + 1e-6):
        f.na = na
        assert F.defence(f, 80) == 0, na
    for d in (0.5, 2, 4, 8):
        assert _close(T(d, 1, 130, True, 0), min(T(d, 1, 140, True), 0.09))
        assert _close(T(d, 1, 130, True), T(d, 1, 130, True, 0))  # nil reads 0
    # past it: 1000 mmol leaves weu at -3109.395032863671 g, so (3109.395032863671 - 1280) / 1920
    f.na = -1000
    r = (3109.395032863671 - 1280) / 1920
    assert _close(F.defence(f, 80), r, 1e-9)
    f.na = -5000
    assert 0.99999 < F.defence(f, 80) <= 1
    # the blend: the capped thirst plus r of what the cap removed; a full defence is ordinary thirst
    assert _close(T(4, 1, 130, True, r), 0.09 + r * (0.70 - 0.09))
    assert _close(T(4, 1, 130, True, 1), 0.70)
    assert _close(T(0.5, 1, 130, True, 1), 0.06)  # under the cap the blend changes nothing
    assert _close(T(8, 1, 130, False, 1), 0.83)  # the kill cap still applies after it
    assert _close(T(2, 1, 140, True, 0.5), 0.25)  # a normal plasma ignores the weight
