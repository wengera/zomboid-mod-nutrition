"""The stomach's two lanes (Plan 11c Task 2; spec § 5a rulings 11c-4, 11c-5 and 11c-8): fill by mass, a solid lane
that empties energy at a zero-order rate rising with the buffered energy (S0131, a labelled inference for solids),
never faster than water's half-time (S1245), and a liquid lane of drunk water whose half-time grows with the solid
lane's energy (S1234 over S1245, a labelled inference). Hand-computed from the constants."""
import math
import os
import re

import pytest

LN2 = 0.6931471805599453
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
STOMACH = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Kernel_Stomach.lua")
NAMES = ("RATE_BASE", "RATE_PER_KCAL", "WATER_HALF_MIN", "LIQUID_PER_KCAL", "CAPACITY_G", "CAPACITY_MAX_G",
         "CAPACITY_HARD_G")


def _vec(host, **kw):
    v = host.K.vector["new"]()
    for k, val in kw.items():
        v[k] = val
    return v


def _closed(E, dtM):
    """The solid fraction in doubles: the closed form of dE/dt = -(1.25 + 0.0025 E), capped at water's."""
    fw = 1 - math.exp(-LN2 * dtM / 13) if dtM > 0 else 0.0
    if E <= 0:
        return fw
    left = (E + 1.25 / 0.0025) * math.exp(-0.0025 * dtM) - 1.25 / 0.0025
    fe = 1.0 if left <= 0 else max(0.0, 1 - left / E)
    return min(fe, fw)


def test_the_constants(host):
    s = host.K.stomach
    assert (s.RATE_BASE, s.RATE_PER_KCAL, s.WATER_HALF_MIN, s.LIQUID_PER_KCAL) == (1.25, 0.0025, 13, 0.12)
    assert (s.CAPACITY_G, s.CAPACITY_MAX_G, s.CAPACITY_HARD_G) == (430, 730, 1100)


def test_each_constant_names_its_row_or_its_label():
    with open(STOMACH, encoding="utf-8") as fh:
        src = fh.read()
    for name in NAMES:
        line = re.search(r"^K\.stomach\.%s = .*$" % name, src, re.M).group(0)
        assert ("labelled inference" in line and re.search(r"S\d{4}", line)) or "S1245 (Mudie" in line, name


def test_mass_of_a_vector_is_its_water_macros_and_fibre_in_grams(host):
    v = _vec(host, calories=95, proteins=0.5, carbs=25.1, lipids=0.3, fibre=4.4, water=155.8, iron=0.2)
    assert host.K.stomach.massOf(v) == pytest.approx(155.8 + 0.5 + 25.1 + 0.3 + 4.4)
    assert host.K.stomach.mass(host.K.stomach["new"]()) == 0


def test_ingest_liquid_puts_the_water_in_the_liquid_lane_and_the_rest_in_the_buffer(host):
    st = host.K.stomach["new"]()
    v = _vec(host, calories=100, carbs=25, water=375, sodium=10)
    out = host.K.stomach.ingestLiquid(st, v)
    assert host.rt.eval("rawequal")(out, st)
    assert st.liquid == 375 and st.buffer.water == 0
    assert (st.buffer.calories, st.buffer.carbs, st.buffer.sodium) == (100, 25, 10)
    assert v.water == 375                                       # the landed vector is left as it was
    assert host.K.stomach.mass(st) == pytest.approx(400)
    assert host.K.stomach.water(st) == pytest.approx(375)


def test_ingest_liquid_keeps_the_buffers_own_water_bit_for_bit(host):
    st = host.K.stomach["new"]()
    host.K.stomach.ingest(st, _vec(host, calories=200, water=0.1))
    host.K.stomach.ingestLiquid(st, _vec(host, water=0.2))
    assert st.buffer.water == 0.1 and st.liquid == pytest.approx(0.2)
    assert host.K.stomach.water(st) == pytest.approx(0.3)


def test_the_solid_rate_rises_with_the_buffered_energy(host):
    assert host.K.stomach.solidRate(0) == 1.25
    assert host.K.stomach.solidRate(600) - host.K.stomach.solidRate(300) == pytest.approx(0.75)   # S0131: +0.72


@pytest.mark.parametrize("E,dtM", [(650, 1), (650, 60), (40, 1), (40, 60), (3, 1), (3, 5), (1, 5)])
def test_the_solid_fraction_is_the_closed_form_capped_at_waters(host, E, dtM):
    assert host.K.stomach.solidFraction(E, dtM) == pytest.approx(_closed(E, dtM), rel=1e-12, abs=1e-15)


def test_a_solid_lane_with_no_energy_empties_like_water(host):
    assert host.K.stomach.solidFraction(0, 13) == pytest.approx(0.5)
    assert host.K.stomach.solidFraction(-1, 13) == pytest.approx(0.5)


def test_no_time_empties_nothing(host):
    assert host.K.stomach.solidFraction(650, 0) == 0
    assert host.K.stomach.waterFraction(0, 13) == 0
    assert host.K.stomach.waterFraction(-5, 13) == 0


def test_the_liquid_half_time_grows_with_the_solid_energy(host):
    assert host.K.stomach.liquidHalfMin(0) == 13
    assert host.K.stomach.liquidHalfMin(500) == pytest.approx(73)
    assert host.K.stomach.liquidHalfMin(-3) == 13


def test_drain_moves_the_solid_share_of_every_key_and_the_liquids_share_of_water(host):
    st = host.K.stomach["new"]()
    host.K.stomach.ingest(st, _vec(host, calories=650, proteins=24.375, carbs=81.25, lipids=25.0, fibre=6, water=300,
                                   iron=4))
    host.K.stomach.ingestLiquid(st, _vec(host, water=250))
    f = _closed(650, 30)
    fl = 1 - math.exp(-LN2 * 30 / (13 + 0.12 * 650))
    em = host.K.stomach.drain(st, 0.5)
    assert em.calories == pytest.approx(650 * f) and em.iron == pytest.approx(4 * f)
    assert em.water == pytest.approx(300 * f + 250 * fl)
    assert st.buffer.calories == pytest.approx(650 * (1 - f)) and st.buffer.water == pytest.approx(300 * (1 - f))
    assert st.liquid == pytest.approx(250 * (1 - fl))
    assert em.fibre == pytest.approx(6 * f) and st.buffer.fibre == pytest.approx(6 * (1 - f))
    loaded = {"calories": 650, "proteins": 24.375, "carbs": 81.25, "lipids": 25.0, "fibre": 6, "iron": 4}
    for key, amount in loaded.items():
        assert em[key] + st.buffer[key] == pytest.approx(amount)


def test_drain_over_no_time_moves_nothing(host):
    st = host.K.stomach["new"]()
    host.K.stomach.ingest(st, _vec(host, calories=95, water=155.8))
    host.K.stomach.ingestLiquid(st, _vec(host, water=100))
    em = host.py(host.K.stomach.drain(st, 0))
    assert all(v == 0 for v in em.values())
    assert st.buffer.calories == 95 and st.liquid == 100

