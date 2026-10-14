"""The strength kernel against the tracked Python references (Plan 13 Tasks 5 and 6; rulings 13-1, 13-37, 13-45).

`K.strength.DEFAULTS` equals Task 2's oracle point (`strength_model.POINT_T`) and Task 2b's level block
(`strength_level.LEVEL_MODEL`) key by key, the bindings of ruling 13-1 for the two blocks; the bio scale, the
shown level, its inverse and R equal the references' to the stated tolerances; the growth law's threshold, set cap,
signal, protein and energy gates and daily growth (with regain and the alcohol gate) equal the oracle's to 1e-12.
"""
import math

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


# ---------------------------------------------------------------- the growth law (Plan 13 Task 6)
GRID_S = (0.0, 0.5, 3.0, 12.0, 20.0, 40.0)
GRID_s = (0.0, 0.5, 0.9, 1.0)
GRID_p = (0.3, 0.8, 1.3, 2.4)
GRID_E = (-1200.0, -500.0, 0.0, 130.0, 400.0)


def _copy(host, **over):
    """A Lua copy of DEFAULTS with the overrides set (the session host is shared, so DEFAULTS is never written)."""
    P = host.rt.table()
    for k, v in _d(host).items():
        P[k] = v
    for k, v in over.items():
        P[k] = v
    return P


def test_threshold_and_set_cap_match_the_oracle(host):
    D = _d(host)
    P = sm.POINT_T
    for s in GRID_s:
        Sg = P["Sg0"] * math.exp(P["beta"] * s)
        Sx = P["Smax"] + (P["Smax1"] - P["Smax"]) * s
        assert abs(host.call("strength.threshold", s, D) - Sg) < 1e-12
        assert abs(host.call("strength.setCap", s, D) - Sx) < 1e-12


def test_signal_matches_the_oracle(host):
    D = _d(host)
    for S in GRID_S:
        for s in GRID_s:
            assert abs(host.call("strength.signal", S, s, D) - sm.Gsig(sm.POINT_T, S, s)) < 1e-12, (S, s)


def test_signal_saturates_at_the_status_set_cap(host):
    D = _d(host)
    for s in GRID_s:
        cap = host.call("strength.setCap", s, D)
        assert host.call("strength.signal", cap, s, D) == host.call("strength.signal", cap + 10, s, D)
    # the cap falls with status: 20 sets a week beat 12 at s = 0 and equal them at s = 1
    assert host.call("strength.signal", 20.0, 0.0, D) > host.call("strength.signal", 12.0, 0.0, D)
    assert host.call("strength.signal", 20.0, 1.0, D) == host.call("strength.signal", 12.0, 1.0, D)


def test_protein_gate_matches_the_oracle(host):
    D = _d(host)
    for p in GRID_p + (0.0, 0.4, 0.6, 1.0, 1.6, 1.9):
        assert abs(host.call("strength.fp", p, D) - sm.fp(sm.POINT_T, p)) < 1e-12, p


def test_energy_gate_matches_the_oracle(host):
    D = _d(host)
    for E in GRID_E + (-650.0, -325.0, 260.0, 1000.0):
        for s in GRID_s:
            for p in GRID_p + (2.0,):
                for tdee in (2600.0, 1900.0):
                    got = host.call("strength.fe", E, s, p, tdee, D)
                    want = sm.fe(sm.POINT_T, E, s, p, tdee)
                    assert abs(got - want) < 1e-12, (E, s, p, tdee)


def test_energy_gate_matches_the_oracle_off_the_point(host):
    # trained_need is 0 at point T; a refit or Angus's premise (1) moves it, and the gate must follow
    over = {"trained_need": 1.0, "full_drop": 0.25, "fbal_drop": 0.3, "E0_drop": 0.2, "a_nov": 2.0}
    for key, val in over.items():
        P = _copy(host, **{key: val})
        Q = dict(sm.POINT_T, **{key: val})
        for E in GRID_E:
            for s in GRID_s:
                for p in GRID_p + (2.0,):
                    got = host.call("strength.fe", E, s, p, 2600.0, P)
                    assert abs(got - sm.fe(Q, E, s, p, 2600.0)) < 1e-12, (key, E, s, p)


def _oracle_grow(F, F0, Fc, Pk, S, p, E, tdee):
    """Body.day's grow before ts (POINT_T: regain gated, max of growth and regain)."""
    P = sm.POINT_T
    b = sm.Body(P, 5.0, 16.5, 10.0)
    b.F, b.F0, b.Fc, b.Pk = F, F0, Fc, Pk
    s = b.s()
    G = sm.Gsig(P, S, s)
    gp = sm.fp(P, p)
    ge = sm.fe(P, E, s, p, tdee)
    grow = P["k"] * (Fc - F) * G * gp * ge / 7.0
    if F < Pk:
        lr = math.log(2) / P["regain_hl_wk"]
        rg = lr * (Pk - F) * min(1.0, G) * gp * ge / 7.0
        grow = max(grow, rg)
    return max(0.0, grow)


def _body(host, lm, F0, Fc, Pk):
    return host.table({"lm": lm, "F0": F0, "Fc": Fc, "Pk": Pk})


def test_growth_matches_the_oracle(host):
    D = _d(host)
    F0 = sm.F_of(5.0)
    Fc = sm.F_of(16.5)
    # at the set point, grown, below a held peak (twice), at the cap and above it (negative room)
    bodies = ((F0, F0), (F0 + 4.0, F0 + 4.0), (F0 + 9.0, F0 + 12.0), (F0 + 1.0, F0 + 6.0),
              (Fc, Fc), (Fc + 2.0, Fc + 2.0))
    for lm, Pk in bodies:
        b = _body(host, lm, F0, Fc, Pk)
        for S in GRID_S:
            for p in GRID_p:
                for E in GRID_E:
                    got = host.call("strength.growth", b, S, p, E, 2600.0, 0.0, D)
                    want = _oracle_grow(lm, F0, Fc, Pk, S, p, E, 2600.0)
                    assert abs(got - want) < 1e-12, (lm, Pk, S, p, E)


def test_alcohol_scales_growth(host):
    D = _d(host)
    F0 = sm.F_of(5.0)
    Fc = sm.F_of(16.5)
    b = _body(host, F0 + 2.0, F0, Fc, F0 + 2.0)
    sober = host.call("strength.growth", b, 15.0, 1.8, 300.0, 2600.0, 0.0, D)
    at = host.call("strength.growth", b, 15.0, 1.8, 300.0, 2600.0, host.K.partition.ALC_THRESH, D)
    drunk = host.call("strength.growth", b, 15.0, 1.8, 300.0, 2600.0, 1.2, D)
    assert sober > 0 and at == sober
    assert abs(drunk - sober * host.K.partition.G_ALC) < 1e-15


def test_alcohol_scales_regain(host):
    # controller ruling (Task 6): regain carries the alcohol gate as growth does
    D = _d(host)
    F0 = sm.F_of(5.0)
    Fc = sm.F_of(16.5)
    lost = _body(host, F0 + 1.0, F0, Fc, F0 + 8.0)
    s = host.call("strength.status", lost)
    G = host.call("strength.signal", 12.0, s, D)
    gates = host.call("strength.fp", 1.8, D) * host.call("strength.fe", 300.0, s, 1.8, 2600.0, D)
    regain = math.log(2) / D["regain_hl_wk"] * 7.0 * min(1.0, G) * gates / 7.0
    grow = D["k"] * (Fc - (F0 + 1.0)) * G * gates / 7.0
    assert regain > grow  # the regain arm is the one returned
    sober = host.call("strength.growth", lost, 12.0, 1.8, 300.0, 2600.0, 0.0, D)
    drunk = host.call("strength.growth", lost, 12.0, 1.8, 300.0, 2600.0, 1.2, D)
    assert abs(sober - regain) < 1e-12
    assert abs(drunk - host.K.partition.G_ALC * sober) < 1e-15


def test_regain_returns_lost_lean_faster_than_growth(host):
    D = _d(host)
    F0 = sm.F_of(5.0)
    Fc = sm.F_of(16.5)
    lost = _body(host, F0 + 1.0, F0, Fc, F0 + 8.0)
    never = _body(host, F0 + 1.0, F0, Fc, F0 + 1.0)
    g_lost = host.call("strength.growth", lost, 12.0, 1.8, 300.0, 2600.0, 0.0, D)
    g_never = host.call("strength.growth", never, 12.0, 1.8, 300.0, 2600.0, 0.0, D)
    assert g_lost > g_never > 0
    # regain is gated by the same signal: no sets, no regain
    assert host.call("strength.growth", lost, 0.0, 1.8, 300.0, 2600.0, 0.0, D) == 0


def test_no_signal_no_growth_whatever_the_protein_and_surplus(host):
    D = host.K.strength.DEFAULTS
    b = host.table({"lm": 52.02, "F0": 52.02, "Fc": 85.3, "Pk": 52.02})
    assert host.call("strength.growth", b, 0.0, 2.4, 400.0, 2600.0, 0.0, D) == 0


def test_low_volume_stalls_where_the_threshold_meets_the_sets(host):
    D = host.K.strength.DEFAULTS
    s = 0.6
    S = host.call("strength.threshold", s, D)
    assert host.call("strength.signal", S, s, D) == 0
    assert host.call("strength.signal", S * 1.01, s, D) > 0
