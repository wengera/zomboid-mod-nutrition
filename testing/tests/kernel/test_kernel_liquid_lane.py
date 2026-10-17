"""The liquid lane slowed only by drink-borne energy (Plan 15 Task 14b; the liquid-emptying report,
docs/superpowers/research/2026-10-16-game-feel/liquid-emptying-report.md).

Water drunk with or after a solid meal separates from it and empties at about its fasting pace (S2265 Houghton 1988's
saline beside a solid meal, median half-time 8 min; S2267 Grimm 2017, as fast as fasted; S2269 Großmann 2025, mostly
emptied within 20 min; S1246, the liquid's emptying uninfluenced by the meal's kcal), and only energy dissolved in the
drink slows it (S1234 Camps 2016's shakes, S2265's dextrose, S2274). So the liquid lane's half-time is
WATER_HALF_MIN + LIQUID_PER_KCAL x min(stomach.liqKcal, the solid lane's kcal), where liqKcal is the energy
ingestLiquid sent to the solid lane, leaving at the solid fraction with the energy it rode in on.
"""
import math

import pytest

from .test_kinetics import KIN, kin_host, run  # noqa: F401  (kin_host is a fixture)

LN2 = 0.6931471805599453
PLATE = {"calories": 667, "carbs": 80, "proteins": 25, "lipids": 25, "water": 570}   # about 700 g, the guide's plate


def _vec(host, **kw):
    v = host.K.vector["new"]()
    for k, val in kw.items():
        v[k] = val
    return v


def _half_minute(host, st):
    """The first whole minute, stepped a minute at a time as the slow clock steps, at which the liquid lane holds half
    of what it held at the start."""
    K = host.K
    l0 = st.liquid
    for m in range(1, 600):
        K.stomach.drain(st, 1 / 60)
        if st.liquid <= l0 / 2:
            return m
    return None


def test_a_fresh_stomach_carries_no_drink_borne_energy(host):
    assert host.K.stomach["new"]().liqKcal == 0


def test_a_drink_adds_its_energy_and_a_food_adds_none(host):
    K = host.K
    st = K.stomach["new"]()
    K.stomach.ingest(st, _vec(host, **PLATE))
    assert st.liqKcal == 0
    K.stomach.ingestLiquid(st, _vec(host, calories=150, carbs=37.5, water=300))
    K.stomach.ingestLiquid(st, _vec(host, water=250))
    assert st.liqKcal == 150
    assert st.buffer.calories == 817


def test_plain_water_beside_a_plate_half_empties_in_waters_13_minutes(host):
    # S2265, S2267, S2269: the plate's 667 kcal no longer slow the drink; the old rule (the lane's whole kcal) read
    # 13 + 0.12 x 667 = 93 min at the start and half-emptied this lane at minute 80 (the report's section 5)
    K = host.K
    st = K.stomach["new"]()
    K.stomach.ingest(st, _vec(host, **PLATE))
    K.stomach.ingestLiquid(st, _vec(host, water=500))
    assert _half_minute(host, st) == 13
    alone = K.stomach["new"]()
    K.stomach.ingestLiquid(alone, _vec(host, water=500))
    assert _half_minute(host, alone) == 13


def test_one_minute_of_water_beside_a_plate_is_waters_fraction(host):
    K = host.K
    st = K.stomach["new"]()
    K.stomach.ingest(st, _vec(host, **PLATE))
    K.stomach.ingestLiquid(st, _vec(host, water=500))
    K.stomach.drain(st, 1 / 60)
    assert st.liquid == pytest.approx(500 * math.exp(-LN2 / 13), rel=1e-12)


def test_a_500_kcal_shake_alone_empties_as_before(host):
    # S1234 (Camps 2016's thin 500 kcal shake, 69.5 min): a drink alone carries all its lane's energy, so the lane
    # steps exactly as the old rule stepped it, 13 + 0.12 x the lane's kcal each minute
    K = host.K
    st = K.stomach["new"]()
    K.stomach.ingestLiquid(st, _vec(host, calories=500, carbs=125, water=300))
    assert K.stomach.liquidHalfMin(K.min(st.liqKcal, st.buffer.calories)) == pytest.approx(73)
    liq, cal = 300.0, 500.0
    for _ in range(120):
        f = K.stomach.solidFraction(cal, 1.0)
        liq = liq * math.exp(-LN2 / (13 + 0.12 * cal))
        cal = cal * (1 - f)
        K.stomach.drain(st, 1 / 60)
        assert st.liquid == pytest.approx(liq, rel=1e-12)
        assert st.liqKcal == pytest.approx(st.buffer.calories, rel=1e-12)


def test_a_shake_beside_a_plate_is_slowed_by_the_shake_alone(host):
    K = host.K
    st = K.stomach["new"]()
    K.stomach.ingest(st, _vec(host, **PLATE))
    K.stomach.ingestLiquid(st, _vec(host, calories=500, carbs=125, water=300))
    K.stomach.drain(st, 1 / 60)
    assert st.liquid == pytest.approx(300 * math.exp(-LN2 / 73), rel=1e-12)


def test_the_counter_leaves_at_the_solid_fraction(host):
    K = host.K
    st = K.stomach["new"]()
    K.stomach.ingest(st, _vec(host, **PLATE))
    K.stomach.ingestLiquid(st, _vec(host, calories=200, carbs=50, water=300))
    f = K.stomach.solidFraction(867, 30)
    K.stomach.drain(st, 0.5)
    assert 0 < f < 1
    assert st.liqKcal == pytest.approx(200 * (1 - f), rel=1e-12)
    assert st.liqKcal / st.buffer.calories == pytest.approx(200 / 867, rel=1e-12)


def test_the_counter_is_capped_at_the_lanes_energy(host):
    K = host.K
    st = K.stomach["new"]()
    K.stomach.ingestLiquid(st, _vec(host, calories=100, carbs=25, water=300))
    st.liqKcal = 900
    K.stomach.drain(st, 1 / 60)
    assert st.liquid == pytest.approx(300 * math.exp(-LN2 / (13 + 0.12 * 100)), rel=1e-12)
    assert st.liqKcal == pytest.approx(st.buffer.calories, rel=1e-12)


def test_the_store_saves_the_counter(host):
    assert "stomach.liqKcal" in list(host.K.store.INPUTS.values())


def test_a_nan_counter_reads_as_the_lanes_energy_and_heals_on_the_step(host):
    # K.min(NaN, E) answers E: the minute drains at the old rule's half-time and the counter comes out finite
    K = host.K
    st = K.stomach["new"]()
    K.stomach.ingest(st, _vec(host, **PLATE))
    K.stomach.ingestLiquid(st, _vec(host, water=500))
    st.liqKcal = math.nan
    f = K.stomach.solidFraction(667, 1.0)
    K.stomach.drain(st, 1 / 60)
    assert st.liquid == pytest.approx(500 * math.exp(-LN2 / (13 + 0.12 * 667)), rel=1e-12)
    assert st.liqKcal == pytest.approx(667 * (1 - f), rel=1e-12)


def test_an_infinite_counter_resets_the_stomach(kin_host):
    h = kin_host
    record = h.rt.eval("""function()
        local K = NutritionRevamp.kernel
        local r = { stomach = K.stomach.new(), pool = K.vector.new(), kineticsAge = 99.0 }
        r.stomach.buffer.water = 50
        r.stomach.buffer.calories = 100
        r.stomach.liqKcal = -1 / 0
        return r
    end""")()
    f0 = KIN(h).stats.failures
    run(h, record, 100.0)
    assert record.stomach.liqKcal == 0 and record.stomach.buffer.water == 0
    assert KIN(h).stats.failures == f0 + 1


def test_a_missing_counter_is_a_malformed_stomach(kin_host):
    h = kin_host
    record = h.rt.eval("""function()
        local K = NutritionRevamp.kernel
        local r = { stomach = K.stomach.new(), pool = K.vector.new(), kineticsAge = 99.0 }
        r.stomach.liqKcal = nil
        return r
    end""")()
    f0 = KIN(h).stats.failures
    run(h, record, 100.0)
    assert record.stomach.liqKcal == 0
    assert KIN(h).stats.failures == f0 + 1
    assert "malformed stomach" in KIN(h).lastError
