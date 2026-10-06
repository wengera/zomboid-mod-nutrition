"""The stomach, gastric emptying and absorption chain (NR_Kernel_Stomach.lua), spec § 4.2 / § 4.4.

NR_Kernel_Stomach.lua is a kernel file (its name is NR_Kernel*), so the session `host` fixture loads
it through its glob and already has NutritionRevamp.kernel.stomach. Every expectation below is
hand-computed from the file's constants: the half-time 2.0 h and the composition scale (S0130/S0131,
open rows shipped as design-phase-v1 game choices), the log-linear iron coefficients -0.0034 per mg
phytic acid (S0195) and +0.0065 per mg ascorbic acid (S0194), the iron bioavailability 0.18 (S0434),
and the fat-co-ingestion shape 1 - exp(-lipids / 3) (the 3 g e-fold, ruling T19-6; S0197/S0199 direction). The tests pass explicit mg
values, so the mechanism is proved independent of the seed table's magnitudes.
"""
import math

LN2 = math.log(2)
TOL = 1e-9


def _vec(host, **kw):
    """A full-schema vector (every declared key 0) with the given keys set."""
    v = host.K.vector["new"]()
    for k, val in kw.items():
        v[k] = val
    return v


def _same(host, a, b):
    """Lua identity: lupa wraps each returned table in a fresh proxy, so == on proxies is not identity."""
    return host.rt.eval("rawequal")(a, b)


def _apple(host):
    return _vec(host, calories=95, fibre=4.4, water=155.8)


# --- constants ---

def test_constants(host):
    s = host.K.stomach
    assert s.HALF_TIME_H == 2.0
    assert s.FULL_BULK == 8.0
    expect = {"water": 1.0, "fibre": 1.0, "vitC": 0.85, "iron": 0.18, "phytate": 0.0,
              "carotene": 0.14, "calcium": 0.25, "magnesium": 0.325}
    for k in ("retinol", "vitD", "vitE", "vitK", "thiamine", "riboflavin", "niacin", "vitB6", "folate", "vitB12",
              "choline", "sodium", "potassium", "zinc", "iodine", "selenium", "efa", "caffeine", "ethanol"):
        expect[k] = 1.0
    assert host.py(s.BIOAVAIL) == expect
    assert s.VITD_FAT_FREE == 0.76


# --- new / bulkOf / ingest ---

def test_new_is_an_empty_buffer(host):
    st = host.py(host.K.stomach["new"]())
    assert st["bulk"] == 0
    assert set(st["buffer"].keys()) == set(host.K.vector.KEYS.values())
    assert all(v == 0 for v in st["buffer"].values())


def test_bulk_of_an_apple(host):
    assert abs(host.K.stomach.bulkOf(_apple(host)) - 4.708) < TOL


def test_ingest_raises_bulk_and_fills_the_buffer(host):
    st = host.K.stomach["new"]()
    out = host.K.stomach.ingest(st, _apple(host))
    assert _same(host, out, st)
    assert abs(st.bulk - 4.708) < TOL
    assert abs(st.buffer.calories - 95) < TOL
    assert abs(st.buffer.fibre - 4.4) < TOL
    assert abs(st.buffer.water - 155.8) < TOL
    host.K.stomach.ingest(st, _apple(host))
    assert abs(st.bulk - 9.416) < TOL
    assert abs(st.buffer.calories - 190) < TOL


# --- compositionScale / emptyFraction ---

def test_composition_scale_of_a_fatty_meal(host):
    assert abs(host.K.stomach.compositionScale(_vec(host, calories=360, lipids=40)) - 2.0) < TOL


def test_composition_scale_fibre_term(host):
    assert abs(host.K.stomach.compositionScale(_vec(host, calories=100, fibre=15)) - 2.0) < TOL


def test_composition_scale_of_a_pure_liquid(host):
    assert host.K.stomach.compositionScale(_vec(host, water=300)) == 0.25


def test_composition_scale_clamps_high(host):
    assert host.K.stomach.compositionScale(_vec(host, calories=1800, lipids=200)) == 3.0


def test_composition_scale_of_an_empty_buffer_is_one(host):
    assert host.K.stomach.compositionScale(_vec(host)) == 1


def test_empty_fraction_one_half_time(host):
    assert abs(host.K.stomach.emptyFraction(2.0, 1.0, 2.0) - 0.5) < TOL


def test_empty_fraction_zero_dt(host):
    assert host.K.stomach.emptyFraction(2.0, 1.0, 0) == 0


def test_empty_fraction_negative_dt(host):
    assert host.K.stomach.emptyFraction(2.0, 1.0, -1) == 0


def test_empty_fraction_slower_for_a_larger_scale(host):
    f = host.K.stomach.emptyFraction(2.0, 2.0, 2.0)
    assert abs(f - (1 - math.exp(-LN2 * 2 / 4))) < TOL
    assert abs(f - 0.2928932188) < 1e-9


# --- empty ---

def test_empty_one_half_time_moves_half_of_every_key(host):
    st = host.K.stomach["new"]()
    host.K.stomach.ingest(st, _vec(host, calories=100, iron=2, vitC=30, water=50))
    bulk0 = st.bulk
    emptied = host.py(host.K.stomach.empty(st, 2.0))
    left = host.py(st.buffer)
    for k, v0 in {"calories": 100, "iron": 2, "vitC": 30, "water": 50}.items():
        assert abs(emptied[k] - v0 / 2) < TOL
        assert abs(left[k] - v0 / 2) < TOL
    assert abs(st.bulk - bulk0 / 2) < TOL


def test_a_fattier_buffer_empties_slower(host):
    st = host.K.stomach["new"]()
    host.K.stomach.ingest(st, _vec(host, calories=360, lipids=40, iron=2))
    emptied = host.py(host.K.stomach.empty(st, 2.0))
    f = 1 - math.exp(-LN2 * 2 / 4)
    assert abs(emptied["lipids"] - 40 * f) < TOL
    assert abs(emptied["iron"] - 2 * f) < TOL
    assert abs(st.buffer.lipids - 40 * (1 - f)) < TOL
    assert abs(st.buffer.calories - 360 * (1 - f)) < TOL


def test_empty_zero_dt_moves_nothing(host):
    st = host.K.stomach["new"]()
    host.K.stomach.ingest(st, _apple(host))
    emptied = host.py(host.K.stomach.empty(st, 0))
    assert all(v == 0 for v in emptied.values())
    assert abs(st.buffer.calories - 95) < TOL


# --- ironFactor / fatFactor ---

def test_iron_factor_phytate(host):
    assert abs(host.K.stomach.ironFactor(250, 0) - math.exp(-0.85)) < TOL
    assert abs(host.K.stomach.ironFactor(250, 0) - 0.4274) < 1e-4


def test_iron_factor_vitamin_c(host):
    assert abs(host.K.stomach.ironFactor(0, 100) - math.exp(0.65)) < TOL
    assert abs(host.K.stomach.ironFactor(0, 100) - 1.9155) < 1e-4


def test_iron_factor_neutral(host):
    assert host.K.stomach.ironFactor(0, 0) == 1


def test_iron_factor_clamps_low(host):
    assert host.K.stomach.ironFactor(2000, 0) == 0.2


def test_iron_factor_clamps_high(host):
    assert host.K.stomach.ironFactor(0, 1000) == 4.0


def test_vitamin_c_counteracts_phytate(host):
    both = host.K.stomach.ironFactor(250, 100)
    assert host.K.stomach.ironFactor(250, 0) < both < host.K.stomach.ironFactor(0, 100)
    assert abs(both - math.exp(-0.85 + 0.65)) < TOL


def test_fat_factor_floor(host):
    assert host.K.stomach.fatFactor(0) == 0.05


def test_fat_factor_28g(host):
    # the e-fold is 3 g (ruling T19-6): 1 - e^(-28/3) at the 28 g reference
    assert abs(host.K.stomach.fatFactor(28) - (1 - math.exp(-28 / 3))) < TOL
    assert abs(host.K.stomach.fatFactor(28) - 0.99991157) < 1e-7


def test_fat_factor_hand_values_at_the_3g_efold(host):
    assert host.K.stomach.FAT_EFOLD_G == 3
    assert abs(host.K.stomach.fatFactor(30) - 0.9999546) < 1e-7        # 1 - e^-10
    assert abs(host.K.stomach.fatFactor(10) - 0.9643260) < 1e-7        # 1 - e^-3.333
    assert abs(host.K.stomach.fatFactor(3) - 0.6321206) < 1e-7         # 1 - e^-1
    assert host.K.stomach.fatFactor(0) == 0.05                         # the floor


def test_fat_factor_clamps_high(host):
    assert host.K.stomach.fatFactor(1000) == 1.0


# --- absorb ---

def test_absorb_phytate_on_magnesium_and_zinc(host):
    # exp(-0.00093 * 983) recomputed in doubles; S0536 (slope), S1084 (the zinc reuse)
    f = math.exp(-0.00093 * 983)
    out = host.py(host.K.stomach.absorb(_vec(host, magnesium=100, zinc=10, phytate=983)))
    assert abs(f - 0.4008) < 1e-4
    assert abs(out["magnesium"] - 100 * 0.325 * f) < TOL
    assert abs(out["zinc"] - 10 * host.K.stomach.BIOAVAIL.zinc * f) < TOL
    plain = host.py(host.K.stomach.absorb(_vec(host, magnesium=100, zinc=10)))
    assert abs(plain["magnesium"] - 32.5) < TOL
    assert abs(plain["zinc"] - 10 * host.K.stomach.BIOAVAIL.zinc) < TOL


def test_absorb_phytate_meal(host):
    emptied = _vec(host, calories=100, iron=10, phytate=250, vitC=0, water=50)
    out = host.py(host.K.stomach.absorb(emptied))
    assert out["calories"] == 100
    assert abs(out["iron"] - 10 * 0.18 * math.exp(-0.85)) < TOL
    assert abs(out["iron"] - 0.7693) < 1e-4
    assert out["phytate"] == 0
    assert abs(out["water"] - 50) < TOL


def test_absorb_vitamin_c_meal(host):
    emptied = _vec(host, iron=10, vitC=100, fibre=6, lipids=12)
    out = host.py(host.K.stomach.absorb(emptied))
    assert abs(out["iron"] - 10 * 0.18 * math.exp(0.65)) < TOL
    assert abs(out["iron"] - 3.448) < 1e-3
    assert abs(out["vitC"] - 85) < TOL
    assert abs(out["fibre"] - 6) < TOL
    assert out["lipids"] == 12


def test_absorb_iron_control_and_a_fresh_vector(host):
    emptied = _vec(host, iron=10)
    out = host.K.stomach.absorb(emptied)
    assert not _same(host, out, emptied)
    assert abs(out.iron - 1.8) < TOL
    assert emptied.iron == 10


# --- the meal context (ruling T17-1, x151r #2981): the factors read the buffer, not the minute's share ---

def _bread_stomach(host):
    st = host.K.stomach.new()
    host.K.stomach.ingest(st, _vec(host, calories=532.0, lipids=6.66, fibre=4.4, water=65.0, iron=6.5,
                                   phytate=400.0, calcium=95.0, magnesium=51.0, zinc=1.8))
    return st


def test_context_reads_the_buffer_into_a_kept_table(host):
    st = _bread_stomach(host)
    st.buffer.vitC = 12.0
    out = host.rt.table()
    got = host.K.stomach.context(st, out)
    assert _same(host, got, out)
    assert (out.phytate, out.vitC, out.calcium, out.lipids) == (400.0, 12.0, 95.0, 6.66)
    fresh = host.K.stomach.context(st)
    assert not _same(host, fresh, out) and fresh.phytate == 400.0


def test_absorb_with_the_meal_context_reads_the_whole_meal(host):
    # the first minute of a 400 mg phytate loaf: 0.18 x exp(-0.0034 x 400) = 0.0461989 per mg emptied,
    # not the 0.179 the minute's ~1 mg share gave (x151r); magnesium and zinc take exp(-0.00093 x 400)
    st = _bread_stomach(host)
    ctx = host.K.stomach.context(st, host.rt.table())
    emptied = host.K.stomach.empty(st, 1 / 60)
    out = host.py(host.K.stomach.absorb(emptied, ctx))
    per_mg = out["iron"] / emptied.iron
    assert abs(per_mg - 0.18 * math.exp(-0.0034 * 400)) < 1e-12
    assert abs(per_mg - 0.046198939851640065) < 1e-12
    assert abs(out["magnesium"] / emptied.magnesium - 0.325 * math.exp(-0.00093 * 400)) < 1e-12
    assert abs(out["zinc"] / emptied.zinc - math.exp(-0.00093 * 400)) < 1e-12
    share = host.py(host.K.stomach.absorb(emptied))  # no ctx: the Plan 2 per-share reading, unchanged
    assert abs(share["iron"] / emptied.iron - 0.18 * math.exp(-0.0034 * emptied.phytate)) < 1e-12
    assert share["iron"] / emptied.iron > 0.179


def test_absorb_with_a_phytate_free_context_is_bare(host):
    emptied = _vec(host, iron=1.0, phytate=0.0, magnesium=10.0)
    ctx = host.rt.table()
    ctx.phytate, ctx.vitC, ctx.calcium, ctx.lipids = 0.0, 0.0, 0.0, 0.0
    out = host.py(host.K.stomach.absorb(emptied, ctx))
    assert abs(out["iron"] - 0.18) < 1e-15
    assert abs(out["magnesium"] - 3.25) < 1e-12
    ctx.vitC = 100.0  # the meal's vitamin C, not the share's
    out = host.py(host.K.stomach.absorb(emptied, ctx))
    assert abs(out["iron"] - 0.18 * math.exp(0.65)) < 1e-12


def test_bioavail_lists_every_non_macro_key(host):
    keys = set(host.K.vector.KEYS.values()) - set(host.K.vector.MACROS.values())
    assert set(host.py(host.K.stomach.BIOAVAIL)) == keys


# --- absorb: the fat factor on the fat-soluble keys (S0197/S0199; vitamin D's floor S0198) ---

FAT_SOLUBLE = ("retinol", "vitE", "vitK")
WATER_SOLUBLE = ("thiamine", "riboflavin", "niacin", "vitB6", "folate", "vitB12", "choline", "sodium",
                 "potassium", "zinc", "iodine", "selenium", "efa", "caffeine", "ethanol")


def _micro_meal(host, lipids):
    kw = {k: 100.0 for k in FAT_SOLUBLE + WATER_SOLUBLE}
    kw.update(carotene=1000.0, vitD=10.0, calcium=400.0, magnesium=80.0, vitC=50.0, lipids=lipids)
    return _vec(host, **kw)


def test_absorb_a_fat_free_meal_floors_the_fat_soluble_keys(host):
    out = host.py(host.K.stomach.absorb(_micro_meal(host, 0)))
    for k in FAT_SOLUBLE:
        assert abs(out[k] - 100 * 0.05) < TOL, k               # the factor's floor
    assert abs(out["vitD"] - 10 * 0.772) < TOL                 # 0.76 + 0.24 x 0.05
    assert abs(out["carotene"] - 1000 * 0.14 * 0.05) < TOL     # S0156 x the floor
    for k in WATER_SOLUBLE:
        assert abs(out[k] - 100) < TOL, k                       # no fat factor, absorb 1.0
    assert abs(out["calcium"] - 100) < TOL                      # 400 x 0.25
    assert abs(out["magnesium"] - 26) < TOL                     # 80 x 0.325
    assert abs(out["vitC"] - 42.5) < TOL
    assert out["lipids"] == 0


def test_absorb_a_30g_fat_meal_takes_the_saturating_factor(host):
    out = host.py(host.K.stomach.absorb(_micro_meal(host, 30)))
    f = 1 - math.exp(-10)
    assert abs(f - 0.9999546) < 1e-7
    for k in FAT_SOLUBLE:
        assert abs(out[k] - 100 * f) < TOL, k
    assert abs(out["vitD"] - 10 * (0.76 + 0.24 * f)) < TOL
    assert abs(out["carotene"] - 1000 * 0.14 * f) < TOL
    for k in WATER_SOLUBLE:
        assert abs(out[k] - 100) < TOL, k
    assert out["lipids"] == 30


def test_absorb_vitamin_d_floor_is_above_the_carotene_floor(host):
    # S0198: vitamin D keeps 0.76 of its fat-meal absorption with no fat; carotene keeps ~0 (S0197).
    out = host.py(host.K.stomach.absorb(_vec(host, vitD=1.0, retinol=1.0)))
    assert out["vitD"] > 0.76 > out["retinol"]


def test_absorb_iron_keeps_its_branch_beside_the_new_keys(host):
    out = host.py(host.K.stomach.absorb(_vec(host, iron=10, phytate=250, calcium=300, lipids=20)))
    assert abs(out["iron"] - 10 * 0.18 * math.exp(-0.85)) < TOL
    assert out["phytate"] == 0
    assert abs(out["calcium"] - 75) < TOL


# --- toPool / fill ---

def test_to_pool_accumulates(host):
    pool = host.K.vector["new"]()
    a = host.K.stomach.absorb(_vec(host, calories=100, vitC=10))
    out = host.K.stomach.toPool(pool, a)
    assert _same(host, out, pool)
    host.K.stomach.toPool(pool, a)
    assert abs(pool.calories - 200) < TOL
    assert abs(pool.vitC - 17) < TOL


def test_fill_fresh_is_zero(host):
    assert host.K.stomach.fill(host.K.stomach["new"]()) == 0


def test_fill_after_an_apple_and_it_falls_on_empty(host):
    st = host.K.stomach["new"]()
    host.K.stomach.ingest(st, _apple(host))
    f0 = host.K.stomach.fill(st)
    assert abs(f0 - 4.708 / 8) < TOL
    assert abs(f0 - 0.5885) < 1e-4
    host.K.stomach.empty(st, 1.0)
    assert host.K.stomach.fill(st) < f0


def test_fill_clamps_at_one(host):
    st = host.K.stomach["new"]()
    host.K.stomach.ingest(st, _vec(host, calories=5000))
    assert host.K.stomach.fill(st) == 1


def test_seed_full_sets_the_bulk_to_full_and_leaves_the_buffer(host):
    # Plan 2 Task 11 game choice: a new record's stomach starts full (the character ate before the apocalypse)
    st = host.K.stomach.new()
    out = host.K.stomach.seedFull(st)
    assert _same(host, out, st)
    assert st["bulk"] == host.K.stomach.FULL_BULK
    assert host.K.stomach.fill(st) == 1.0
    assert all(st["buffer"][k] == 0 for k in host.K.vector.KEYS.values())


# --- the fat factor reads the meal's lipids (ruling T19-1, the Plan 4 close) ---

def test_absorb_with_a_context_reads_the_meals_lipids(host):
    # the first minute of a 30 g-fat meal: the factor reads the buffer's 30 g (0.99995), not the
    # minute's ~0.1 g share (which floored at 0.05)
    st = host.K.stomach.new()
    host.K.stomach.ingest(st, _vec(host, lipids=30.0, retinol=900.0, vitK=120.0, vitD=15.0))
    ctx = host.K.stomach.context(st, host.rt.table())
    emptied = host.K.stomach.empty(st, 1 / 60)
    out = host.py(host.K.stomach.absorb(emptied, ctx))
    f = 1 - math.exp(-10.0)
    assert abs(f - 0.9999546000702375) < 1e-12
    assert abs(out["retinol"] / emptied.retinol - f) < 1e-12
    assert abs(out["vitK"] / emptied.vitK - f) < 1e-12
    assert abs(out["vitD"] / emptied.vitD - (0.76 + (1 - 0.76) * f)) < 1e-12
    share = host.py(host.K.stomach.absorb(emptied))  # no ctx: the per-share reading, unchanged
    assert abs(share["retinol"] / emptied.retinol - 0.05) < 1e-12


def _meal_replay_py(n=1440):
    """K.stomach.ingest/context/empty/absorb recomputed in doubles over n one-minute steps of one meal."""
    b = dict(lipids=30.0, retinol=900.0, vitK=120.0, vitD=15.0)
    tot = dict(retinol=0.0, vitK=0.0, vitD=0.0)
    for _ in range(n):
        lip = b["lipids"]                                            # the context, before the emptying
        cs = min(max(1 + b["lipids"] / 40 + 0.0 / 15, 0.5), 3.0)
        f = 1 - math.exp(-0.6931471805599453 * (1 / 60) / (2.0 * cs))
        em = {k: 0 + v * f for k, v in b.items()}
        for k in b:
            b[k] = b[k] * (1 - f)
        fat = min(max(1 - math.exp(-lip / 3), 0.05), 1.0)
        tot["retinol"] += em["retinol"] * 1.0 * fat
        tot["vitK"] += em["vitK"] * 1.0 * fat
        tot["vitD"] += em["vitD"] * 1.0 * (0.76 + (1 - 0.76) * fat)
    return tot, b


MEAL_REPLAY = r"""
function(n)
    local K = NutritionRevamp.kernel
    local st = K.stomach.new()
    local meal = K.vector.new()
    meal.lipids = 30
    meal.retinol = 900
    meal.vitK = 120
    meal.vitD = 15
    K.stomach.ingest(st, meal)
    local ctx = {}
    local tot = { retinol = 0, vitK = 0, vitD = 0 }
    for i = 1, n do
        K.stomach.context(st, ctx)
        local out = K.stomach.absorb(K.stomach.empty(st, 1 / 60), ctx)
        tot.retinol = tot.retinol + out.retinol
        tot.vitK = tot.vitK + out.vitK
        tot.vitD = tot.vitD + out.vitD
    end
    return tot, st.buffer.lipids
end
"""


def test_a_30g_fat_meal_over_a_day_absorbs_the_replayed_fraction(host):
    # Rulings T19-1 and T19-6 at the Plan 4 close: the buffer's lipids empty with the vitamins, so the factor
    # 1 - exp(-L/3) eases over the meal; the replay in doubles gives 0.900358 of the retinol and vitK, meeting
    # the brief's >= 0.9 (the 10 g e-fold gave 0.684236).
    exp_tot, exp_buf = _meal_replay_py()
    tot, lip = host.rt.eval(MEAL_REPLAY)(1440)
    assert abs(exp_tot["retinol"] / 900 - 0.9003579863810677) < 1e-12
    assert abs(tot.retinol / 900 - exp_tot["retinol"] / 900) < 1e-6
    assert abs(tot.vitK / 120 - exp_tot["vitK"] / 120) < 1e-6
    assert abs(tot.vitK / 120 - 0.9003579863810661) < 1e-6
    # vitamin D at 0.76 + 0.24 x the factor per minute: 0.975693 of the dose
    assert abs(tot.vitD / 15 - exp_tot["vitD"] / 15) < 1e-6
    assert abs(tot.vitD / 15 - 0.9756926315613453) < 1e-6
    assert abs(lip - exp_buf["lipids"]) < 1e-9                       # 0.0155 g left after the day
    # the per-share reading this ruling replaced absorbed 5 % (the floor) of the same meal
    assert tot.retinol / 900 > 18 * 0.05
