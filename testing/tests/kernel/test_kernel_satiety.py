"""The satiety scalar S (Plan 11 Task 15; Decision 2 (c), Appendix D): NR_Kernel_Satiety.lua on the kernel host."""
import math

import pytest


def test_the_rate_follows_vanillas_branches(host):
    r = host.call("satiety.defaults")
    assert host.call("satiety.rate", r, False, False, False) == pytest.approx(9.6e-6)      # #0470
    assert host.call("satiety.rate", r, False, False, True) == 0                           # the freeze, #0473
    assert host.call("satiety.rate", r, True, False, False) == pytest.approx(1.0e-6)       # #0472
    assert host.call("satiety.rate", r, True, False, True) == 0
    assert host.call("satiety.rate", r, False, True, True) == pytest.approx(1.92e-5)       # exercise never freezes
    assert host.call("satiety.rate", r, False, True, False) == pytest.approx(1.92e-5 / 3)  # #0471


def test_traits_scale_the_rate(host):
    assert host.call("satiety.trait", True, False) == 1.5 and host.call("satiety.trait", False, True) == 0.75
    assert host.call("satiety.trait", False, False) == 1


def test_a_step_decays_s_exponentially(host):
    s = host.call("satiety.step", 0.8, 3600, 9.6e-6, 1, 1)
    assert s == pytest.approx(0.8 * math.exp(-9.6e-6 * 3600))


def test_a_step_scales_by_the_sandbox_multiplier_and_the_trait(host):
    s = host.call("satiety.step", 0.8, 3600, 9.6e-6, 2, 1.5)
    assert s == pytest.approx(0.8 * math.exp(-9.6e-6 * 2 * 1.5 * 3600))


def test_relief_and_the_bulk_factor(host):
    assert host.call("satiety.relief", -0.36, 0.5) == pytest.approx(0.18)
    assert host.call("satiety.bulkFactor", 8.0, 8.0, 1 / 2.5079, 0.25) == pytest.approx(1.0)
    f = host.call("satiety.bulkFactor", 8.0, 8.0, 0.36, 0.25)
    assert f == pytest.approx(min(max((1.0 / 0.36) / 2.5079, 0.25), 4.0) ** 0.25)
    assert host.call("satiety.bulkFactor", 100.0, 8.0, 0.01, 0.5) == pytest.approx(4.0 ** 0.5)   # clamped at 4
    assert host.call("satiety.bulkFactor", 8.0, 8.0, 0.0, 0.25) == 1
    assert host.call("satiety.bulkFactor", 8.0, 8.0, 0.36, 0.0) == 1


def test_the_bulk_factor_is_clamped_below_at_a_quarter(host):
    assert host.call("satiety.bulkFactor", 0.01, 8.0, 0.36, 0.5) == pytest.approx(0.25 ** 0.5)
    assert host.call("satiety.bulkFactor", 0.0, 8.0, 0.36, 0.5) == pytest.approx(0.25 ** 0.5)   # zero bulk: the floor, never 1
    assert host.call("satiety.bulkFactor", 8.0, 0.0, 0.36, 0.25) == 1


def test_the_constants_are_appendix_ds(host):
    S = host.K.satiety
    assert (S.R0, S.LO, S.HI, S.BETA, S.HEARTY, S.LIGHT) == (2.5079, 0.25, 4, 0.25, 1.5, 0.75)


def test_add_caps_at_one_and_seed_reads_one_minus_hunger(host):
    assert host.call("satiety.add", 0.9, 0.3, 1.0) == 1
    assert host.call("satiety.add", 0.5, 0.2, 1.5) == pytest.approx(0.8)
    assert host.call("satiety.seed", 0.31) == pytest.approx(0.69)
    assert host.call("satiety.seed", 1.4) == 0
    assert host.call("satiety.seed", -0.2) == 1
