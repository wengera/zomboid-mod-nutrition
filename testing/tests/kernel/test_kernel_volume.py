"""Fullness by weight and volume (Plan 15 Task 7): the satiety mass reads K.satiety.BETA of a solid food's plate volume
beyond its weight (stomach.volX), from the SR Legacy household measures the generated table carries
(NR.data.volume, tools/food_nutrients.py); the physical stomach and its 730 and 1100 g caps stay on mass.

The worked examples are the volume report's section 5 (docs/superpowers/research/2026-10-16-game-feel/volume-report.md@program-record-v19),
read through the mod's own items: fill = w + BETA x (V - w), with w the vector's mass (K.stomach.massOf) and V its
plate volume (ml_per_g x w).
"""
import math
import os

import pytest

from .server_host import Host
from .test_kinetics import KIN, kin_host, run  # noqa: F401  (kin_host is a fixture)

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Data_Nutrients.lua")


@pytest.fixture(scope="module")
def vh(host):
    with open(DATA, encoding="utf-8") as fh:
        src = fh.read()
    host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@NR_Data_Nutrients.lua")()
    return host


def data(h):
    return h.G.NutritionRevamp.data


def eat(h, full_type, grams=None, ml=True):
    """A fresh stomach holding one item's vector (scaled to `grams` of mass when given), its volume from the table."""
    K = h.K
    vec = data(h).nutrients.get(full_type)
    if grams is not None:
        vec = K.vector.add(K.vector.new(), vec, grams / K.stomach.massOf(vec))
    st = K.stomach.new()
    K.stomach.ingest(st, vec, data(h).volume.get(full_type) if ml else None)
    return st, K.stomach.massOf(vec)


def at_beta(h, beta, fn):
    saved = h.K.satiety.BETA
    h.K.satiety.BETA = beta
    try:
        return fn()
    finally:
        h.K.satiety.BETA = saved


def test_beta_is_the_evidences_point(vh):
    assert vh.K.satiety.BETA == 0.05


@pytest.mark.parametrize("full_type,grams,ml,fill,band", [
    ("Base.Broccoli", 1000.0, 2.5999, 1080.0, 1.0),      # 1 kg raw broccoli (170379, 1 cup chopped = 91 g): 1080
    ("Base.BreadSlices", None, 6.7597, 86.0, 3.0),        # the BreadSlices item (174924, 1 cup cubes = 35 g): 86
    # the Popcorn item (173141, 1 cup = 7.9 g): the report's 55 at its 22.4 g portion; the mod's vector weighs 23.9 g
    # (K.stomach.massOf counts the fibre beside the carbohydrate that holds it), so it reads 58.5
    ("Base.Popcorn", None, 29.9478, 58.5, 1.0),
])
def test_the_worked_examples(vh, full_type, grams, ml, fill, band):
    h = vh
    assert data(h).volume.get(full_type) == ml
    st, w = eat(h, full_type, grams)
    got = h.K.stomach.satietyMass(st)
    assert got == pytest.approx(w + 0.05 * (ml - 1) * w, rel=1e-12)
    assert abs(got - fill) <= band, (full_type, w, got)
    assert got > w


def test_500_ml_of_water_reads_its_weight_at_any_beta(vh):
    h = vh
    K = h.K
    vec = K.vector.add(K.vector.new(), data(h).fluids.get("Water"), 0.5)
    st = K.stomach.new()
    K.stomach.ingestLiquid(st, vec)
    assert K.stomach.mass(st) == pytest.approx(500.0, abs=1.0)            # 999 g of water in the litre
    assert st.volX == 0
    plain = at_beta(h, 0, lambda: K.stomach.satietyMass(st))
    assert K.stomach.satietyMass(st) == plain == pytest.approx(K.satiety.LIQUID_WEIGHT * K.stomach.mass(st), rel=1e-12)
    assert data(h).volume.get("Water") == 1.0


def test_the_physical_fill_never_reads_beta(vh):
    h = vh
    K = h.K
    st, w = eat(h, "Base.Popcorn", 400.0)
    assert st.volX > 0
    for beta in (0, 0.05, 0.1):
        mass, fill, food = at_beta(h, beta, lambda: (K.stomach.mass(st), K.stomach.fill(st), K.stomach.foodFill(st)))
        assert mass == pytest.approx(w, rel=1e-12)
        assert fill == pytest.approx(K.satiety.fill(w, K.stomach.CAPACITY_MAX_G), rel=1e-12)
        assert food == fill
    assert at_beta(h, 0, lambda: K.stomach.satietyMass(st)) == pytest.approx(w, rel=1e-12)
    assert at_beta(h, 0.1, lambda: K.stomach.satietyMass(st)) > K.stomach.satietyMass(st)


def test_a_dense_food_reads_slightly_under_its_weight_and_never_below_zero(vh):
    h = vh
    st, w = eat(h, "Base.CannedBolognese")
    assert data(h).volume.get("Base.CannedBolognese") == 0.9617
    got = h.K.stomach.satietyMass(st)
    assert 0 < got < w
    assert got == pytest.approx(w * (1 + 0.05 * (0.9617 - 1)), rel=1e-12)


def test_no_ml_per_g_adds_no_volume(vh):
    st, w = eat(vh, "Base.Popcorn", ml=False)
    assert st.volX == 0
    assert vh.K.stomach.satietyMass(st) == pytest.approx(w, rel=1e-12)
    assert vh.K.stomach.new().volX == 0


def test_an_unmapped_type_reads_one(vh):
    assert data(vh).volume.get("Base.NoSuchFood") == 1.0
    assert data(vh).volume.get("Base.Steak") == 1.0          # no household measure: by weight alone


def test_the_excess_leaves_with_the_solids(vh):
    h = vh
    K = h.K
    st, w = eat(h, "Base.BreadSlices")
    x0, m0, e0 = st.volX, K.stomach.massOf(st.buffer), st.buffer.calories
    K.stomach.drain(st, 0.5)
    left = st.buffer.calories / e0
    assert 0 < left < 1
    assert st.volX == pytest.approx(x0 * left, rel=1e-12)
    assert st.volX / K.stomach.massOf(st.buffer) == pytest.approx(x0 / m0, rel=1e-12)


def test_two_foods_add_their_excesses(vh):
    h = vh
    K = h.K
    st = K.stomach.new()
    for t in ("Base.BreadSlices", "Base.Popcorn", "Base.CannedBolognese"):
        vec = data(h).nutrients.get(t)
        K.stomach.ingest(st, vec, data(h).volume.get(t))
    want = sum((data(h).volume.get(t) - 1) * K.stomach.massOf(data(h).nutrients.get(t))
               for t in ("Base.BreadSlices", "Base.Popcorn", "Base.CannedBolognese"))
    assert st.volX == pytest.approx(want, rel=1e-12)


def test_the_store_saves_the_excess(host):
    S = host.K.store
    assert "stomach.volX" in list(S.INPUTS.values())


def test_a_nan_excess_resets_the_stomach(kin_host):
    h = kin_host
    record = h.rt.eval("""function()
        local K = NutritionRevamp.kernel
        local r = { stomach = K.stomach.new(), pool = K.vector.new(), kineticsAge = 99.0 }
        r.stomach.buffer.water = 50
        r.stomach.volX = 0 / 0
        return r
    end""")()
    f0 = KIN(h).stats.failures
    run(h, record, 100.0)
    assert record.stomach.volX == 0 and record.stomach.buffer.water == 0
    assert KIN(h).stats.failures == f0 + 1


def test_a_missing_excess_is_a_malformed_stomach(kin_host):
    h = kin_host
    record = h.rt.eval("""function()
        local K = NutritionRevamp.kernel
        local r = { stomach = K.stomach.new(), pool = K.vector.new(), kineticsAge = 99.0 }
        r.stomach.volX = nil
        return r
    end""")()
    f0 = KIN(h).stats.failures
    run(h, record, 100.0)
    assert record.stomach.volX == 0
    assert KIN(h).stats.failures == f0 + 1
    assert "malformed stomach" in KIN(h).lastError


def test_the_writer_reads_a_nan_excess_as_unfinished():
    h = Host()
    st = h.K.stomach.new()
    W = h.NR.server.writer
    assert W.bufferFinite(st) is True
    st.volX = math.nan
    assert W.bufferFinite(st) is False


def test_the_intake_lands_an_eat_with_its_items_volume():
    h = Host()
    IN = h.NR.server.intake
    assert IN.volumeOf("Base.Popcorn") == 29.9478
    assert IN.volumeOf("Base.NoSuchFood") == 1.0
    assert IN.volumeOf(None) == 1.0
    K = h.K
    record = h.rt.eval("function() local K = NutritionRevamp.kernel return { stomach = K.stomach.new(), "
                       "satiety = {} } end")()
    vec = h.NR.data.nutrients.get("Base.Popcorn")
    w = K.stomach.massOf(vec)
    IN.land(record, "v", vec, None, IN.volumeOf("Base.Popcorn"))
    assert record.stomach.volX == pytest.approx(28.9478 * w, rel=1e-12)
    drink = K.vector.add(K.vector.new(), h.NR.data.fluids.get("Water"), 0.25)
    IN.land(record, "v", drink, "liquid")
    assert record.stomach.volX == pytest.approx(28.9478 * w, rel=1e-12)


# --- Plan 15 Task 7 fix 1: the volume oracles (gut_oracles.py, review F1) --------------------------------------------

from . import gut_oracles as G  # noqa: E402

VOLUME_ORACLES = ("nguyen_popcorn_below_chips", "osterholt_null")


def _volume_readings(h, beta):
    return at_beta(h, beta, lambda: {"volume": G.volume_snacks(h)})


def test_the_volume_oracles_hold_at_the_shipped_beta(host):
    got = G.check(_volume_readings(host, host.K.satiety.BETA), *VOLUME_ORACLES)
    # Plan 15 Task 14b: each arm's 200 mL of water now leaves at water's half-time beside the snack (the liquid lane
    # reads drink-borne kcal only), so both arms read hungrier and the gap widens from -0.005392 to -0.006049
    assert got["nguyen_popcorn_below_chips"] == pytest.approx(-0.006049, abs=1e-6)   # S2209: the popcorn arm below
    assert got["osterholt_null"] == pytest.approx(0.002815, abs=1e-6)                # S1484: inside +/- 0.0096


def test_nguyens_sign_fails_without_the_volume_term(host):
    # the stability check: at BETA = 0 the chips' larger meal pool wins, so the oracle reads the volume term itself
    r = _volume_readings(host, 0)
    o = G.BY_NAME["nguyen_popcorn_below_chips"]
    assert o.pick(r) == pytest.approx(0.000304, abs=1e-6)       # 0.000960 before Plan 15 Task 14b's liquid lane
    assert o.miss(o.pick(r)) > 0
    assert G.BY_NAME["osterholt_null"].miss(G.BY_NAME["osterholt_null"].pick(r)) == 0     # the null holds at 0 too


def test_osterholts_null_fails_at_ten_times_beta(host):
    r = _volume_readings(host, 10 * host.K.satiety.BETA)
    o = G.BY_NAME["osterholt_null"]
    assert o.pick(r) == pytest.approx(-0.011792, abs=1e-6)
    assert o.miss(o.pick(r)) > 0
