"""The strength kernel against the tracked Python references (Plan 13 Task 5; rulings 13-1 and 13-45).

`K.strength.DEFAULTS` equals Task 2's oracle point (`strength_model.POINT_T`) and Task 2b's level block
(`strength_level.LEVEL_MODEL`) key by key, the bindings of ruling 13-1 for the two blocks; the bio scale, the
shown level, its inverse and R equal the references' to the stated tolerances.
"""
from . import strength_model as sm
from . import strength_level as sl


def _d(host):
    return host.K.strength.DEFAULTS


def test_defaults_equal_the_oracle_point(host):
    D = _d(host)
    for k, v in sm.POINT_T.items():
        if k in ("fp_knots", "infeasible", "regain_gated", "regain_sum"):
            continue
        assert D[k] == v, k
    knots = D["fp_knots"]
    for i, (x, y) in enumerate(sm.POINT_T["fp_knots"]):
        assert knots[i + 1][1] == x and knots[i + 1][2] == y


def test_level_block_equals_the_reference(host):
    D = _d(host)
    for k, v in sl.LEVEL_MODEL.items():
        if isinstance(v, dict):
            for t, x in v.items():
                assert D[k][t] == x, (k, t)
        else:
            assert D[k] == v, k
    assert abs(D["M5"] - sl.M5) < 1e-12
    assert abs(D["R"] - sl.R_of(D["yearsTo10"])) < 1e-12


def test_bio_scale_matches_the_oracle(host):
    D = _d(host)
    for L in (0.0, 3.0, 5.0, 9.0, 14.0, 16.5, 18.5):
        assert abs(host.call("strength.fOfBio", L, D) - sm.F_of(L)) < 1e-12
        assert abs(host.call("strength.bioLevel", sm.F_of(L), D) - L) < 1e-12


def test_level_matches_the_reference_and_inverts(host):
    D = _d(host)
    for F in (20.0, 26.5, 27.0, 42.115, 52.02, 60.857, 73.056):
        for N0 in (0.82, 1.0, 1.14):
            for T in (1.0, 1.05, 1.10):
                assert abs(host.call("strength.level", F, N0, T, D) - sl.level(F, N0, T)) < 1e-12
    for L in (1.0, 3.0, 5.0, 7.0, 9.0, 12.3):
        F = host.call("strength.fOfLevel", L, 1.07, 1.0, D)
        assert abs(host.call("strength.level", F, 1.07, 1.0, D) - L) < 1e-12


def test_R_reads_the_years_only(host):
    for y in (1.0, 1.3, 2.0, 2.5, 4.0, 4.5, 10.0):
        assert abs(host.call("strength.R", y) - sl.R_of(y)) < 1e-12


def test_shown_level_and_bar(host):
    n, frac = host.call("strength.shown", 7.25)
    assert n == 7 and abs(frac - 0.25) < 1e-12
    n, frac = host.call("strength.shown", 6.999999999999997)
    assert n == 7 and frac == 0
    n, frac = host.call("strength.shown", 12.3)
    assert n == 10 and frac == 0
    n, frac = host.call("strength.shown", -0.4)
    assert n == 0 and frac == 0


def test_status(host):
    b = host.table({"lm": 60.0, "F0": 52.0, "Fc": 68.0})
    assert abs(host.call("strength.status", b) - 0.5) < 1e-12
    b = host.table({"lm": 50.0, "F0": 52.0, "Fc": 52.0})
    assert host.call("strength.status", b) == 0
