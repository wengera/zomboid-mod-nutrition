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
            for p in GRID_p + (2.0, 3.0):
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
    regain = math.log(2) / D["regain_hl_wk"] * (8.0 - 1.0) * min(1.0, G) * gates / 7.0
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


def test_growth_reads_its_own_keys(host):
    # decoys: keys with point-T values equal to growth's own, moved apart; the kernel must still match the oracle
    D = _d(host)
    decoy = _copy(host, pdef_lo=0.7, pdef_hi=2.2, xs_p0=0.9, xs_pspan=0.6, detrain_hl_wk=9.0)
    for E in GRID_E:
        for s in GRID_s:
            for p in GRID_p + (2.0, 3.0):
                assert abs(host.call("strength.fe", E, s, p, 2600.0, decoy) - sm.fe(sm.POINT_T, E, s, p, 2600.0)) < 1e-12
    F0 = sm.F_of(5.0)
    Fc = sm.F_of(16.5)
    for key, val in {"regain_hl_wk": 4.0, "Smax1": 18.0, "Sref": 10.0, "Smax": 25.0}.items():
        P = _copy(host, **{key: val})
        Q = dict(sm.POINT_T, **{key: val})
        for lm, Pk in ((F0 + 1.0, F0 + 8.0), (F0 + 9.0, F0 + 9.0)):
            b = _body(host, lm, F0, Fc, Pk)
            for S in GRID_S:
                ob = sm.Body(Q, 5.0, 16.5, 10.0)
                ob.F, ob.F0, ob.Fc, ob.Pk = lm, F0, Fc, Pk
                s = ob.s()
                G = sm.Gsig(Q, S, s)
                g = sm.fp(Q, 1.8) * sm.fe(Q, 300.0, s, 1.8, 2600.0)
                grow = Q["k"] * (Fc - lm) * G * g / 7.0
                if lm < Pk:
                    grow = max(grow, math.log(2) / Q["regain_hl_wk"] * (Pk - lm) * min(1.0, G) * g / 7.0)
                got = host.call("strength.growth", b, S, 1.8, 300.0, 2600.0, 0.0, P)
                assert abs(got - max(0.0, grow)) < 1e-12, (key, lm, S)


# ---------------------------------------------------------------- the lean partition (Plan 13 Task 7)
# The oracle's exact day (ruling 13-2) from a body with grace 0, so no detraining runs on the compared day; the
# kernel's arm is called with the oracle's scaled growth and must reproduce the oracle's lean, labile and fat change.
from . import strength_oracles as so

EXACT = dict(sm.POINT_T, exact=True)

# (name, bio level, fat kg, S, p, E, tdee): the daily inputs of strength_oracles' helpers (_longland, the Mettler
# shares, _bray, and the section 9 checks chk1, chk2, chk4 and the +2 % degenerate check at s = 0.9)
PARTITION_CASES = (
    ("longland_hp", 5.0, 25.0, 20, 2.4, -1200.0, 3000.0),
    ("longland_lp", 5.0, 25.0, 20, 1.2, -1200.0, 3000.0),
    ("mettler_lp", so.L_at_s(0.4), 12.0, 12, 1.0, -1200.0, 3000.0),
    ("mettler_hp", so.L_at_s(0.4), 12.0, 12, 2.3, -1200.0, 3000.0),
    ("bray_15", 5.0, 20.0, 0, 1.8, 954.0, 2400.0),
    ("bray_5", 5.0, 20.0, 0, 0.6, 954.0, 2400.0),
    ("chk1_s09_bal", so.L_at_s(0.9), 9.0, 15, 2.0, 0.0, 2900.0),
    ("chk2_s09_surplus10", so.L_at_s(0.9), 9.0, 15, 2.0, 0.10 * 2900, 2900.0),
    ("chk4_s09_contest", so.L_at_s(0.9), 3.5, 15, 2.5, -500.0, 2900.0),
    ("deg_s09_surplus2", so.L_at_s(0.9), 9.0, 15, 2.0, 0.02 * 2900, 2900.0),
)
# deficit inputs (S, p, E, tdee) applied to a body carrying labile lean (the Bray state), so lx pays in part and in full
CROSS_DEFICITS = (
    (20, 2.4, -1200.0, 3000.0),
    (12, 1.0, -1200.0, 3000.0),
    (12, 2.3, -60.0, 3000.0),
    (15, 2.5, -20.0, 2900.0),
    (0, 0.6, -800.0, 2400.0),
    (0, 0.6, -1200.0, 2400.0),
)
# surplus inputs on the same body: growth eats the whole surplus (lx decays), or leaves some (lx grows to its cap)
CROSS_SURPLUS = (
    (15, 2.0, 0.0, 2600.0),
    (20, 2.0, 15.0, 2600.0),
    (0, 1.8, 300.0, 2400.0),
)
TS_GRID = (1.0, 2.5)


def _oracle_body(Q, L, fat, days, S, p, E, tdee):
    """The helper body (body_at, Pk = F), run `days` days of Q on its own inputs."""
    b = so.body_at(Q, L, fat)
    b.Pk = b.F
    so.run(b, days, S, p, E, tdee)
    return b


def _clone(Q, ob):
    c = sm.Body(Q, 5.0, 16.5, 10.0)
    c.F, c.F0, c.Fc, c.Pk, c.M, c.X = ob.F, ob.F0, ob.Fc, ob.Pk, ob.M, ob.X
    c.grace = 0
    return c


def _oracle_grow_q(Q, ob, S, p, E, tdee):
    """Body.day's grow before ts, under Q (regain gated, max of growth and regain)."""
    s = ob.s()
    G = sm.Gsig(Q, S, s)
    gp = sm.fp(Q, p)
    ge = sm.fe(Q, E, s, p, tdee)
    grow = Q["k"] * (ob.Fc - ob.F) * G * gp * ge / 7.0
    if ob.F < ob.Pk:
        grow = max(grow, math.log(2) / Q["regain_hl_wk"] * (ob.Pk - ob.F) * min(1.0, G) * gp * ge / 7.0)
    return max(0.0, grow)


def _oracle_step(Q, ob, S, p, E, tdee):
    """One exact oracle day from a clone of ob (grace 0: no detraining): the scaled growth and the F, X, M changes."""
    c = _clone(Q, ob)
    grow = _oracle_grow_q(Q, c, S, p, E, tdee) * Q.get("ts", 1.0)
    F, X, M = c.F, c.X, c.M
    c.day(S, p, E, tdee)
    assert c.F > 0.35 * c.F0 and c.M > 0.5  # the floors never bind on a compared day
    return grow, c.F - F, c.X - X, c.M - M


def _lua_body(host, ob):
    return host.table({"lm": ob.F, "lx": ob.X, "fm": ob.M, "F0": ob.F0, "Fc": ob.Fc, "Pk": ob.Pk})


def _kernel_arm(host, P, ob, grow, S, p, E, ts):
    """The kernel arm by the sign of E, as dF (the partition's own lean change, growth excluded), dX, dM."""
    b = _lua_body(host, ob)
    if E >= 0:
        dX, dM = host.call("partition.surplusLean", b, grow, S, p, E, P, ts)
        return 0.0, dX, dM
    return host.call("partition.deficitLean", b, grow, S, p, E, P, ts)


def _assert_parity(host, P, Q, ob, S, p, E, tdee, label):
    grow, dF_o, dX_o, dM_o = _oracle_step(Q, ob, S, p, E, tdee)
    dF, dX, dM = _kernel_arm(host, P, ob, grow, S, p, E, Q.get("ts", 1.0))
    assert abs(dX - dX_o) < 1e-12, (label, "dX", dX, dX_o)
    assert abs(dM - dM_o) < 1e-12, (label, "dM", dM, dM_o)
    assert abs((grow + dF) - dF_o) < 1e-12, (label, "lean", grow + dF, dF_o)
    return dF, dX, dM


def _states(Q, L, fat, S, p, E, tdee):
    days = (0, 5, 40, 150) if E >= 0 else (0, 5, 40)
    return [(d, _oracle_body(Q, L, fat, d, S, p, E, tdee)) for d in days]


def test_partition_arms_match_the_exact_oracle(host):
    D = _d(host)
    for ts in TS_GRID:
        Q = dict(EXACT, ts=ts)
        for name, L, fat, S, p, E, tdee in PARTITION_CASES:
            for d, ob in _states(Q, L, fat, S, p, E, tdee):
                _assert_parity(host, D, Q, ob, S, p, E, tdee, (name, d, ts))
        for d in (1, 40, 150):
            ob = _oracle_body(Q, 5.0, 20.0, d, 0, 1.8, 954.0, 2400.0)
            for S, p, E, tdee in CROSS_SURPLUS:
                _assert_parity(host, D, Q, ob, S, p, E, tdee, ("cross surplus", d, ts, S, p, E))


def test_labile_lean_pays_a_deficit_first(host):
    D = _d(host)
    paid_in_full = paid_in_part = 0
    for ts in TS_GRID:
        Q = dict(EXACT, ts=ts)
        for d in (1, 5, 40, 150):
            ob = _oracle_body(Q, 5.0, 20.0, d, 0, 1.8, 954.0, 2400.0)
            assert ob.X > 0
            for S, p, E, tdee in CROSS_DEFICITS:
                dF, dX, dM = _assert_parity(host, D, Q, ob, S, p, E, tdee, ("cross", d, ts, S, p, E))
                if dF == 0:
                    paid_in_full += 1  # lx covered the whole lean loss, the rest of it decays
                    assert -ob.X < dX < 0
                else:
                    paid_in_part += 1  # lx spent to 0, F paid the rest
                    assert dF < 0 and abs(dX + ob.X) < 1e-15
    assert paid_in_full > 0 and paid_in_part > 0


def test_labile_lean_decays_on_a_day_with_no_surplus_left(host):
    D = _d(host)
    RL = host.K.partition.RHO_LEAN
    RF = host.K.partition.RHO_FAT
    ob = _oracle_body(EXACT, 5.0, 20.0, 40, 0, 1.8, 954.0, 2400.0)
    b = _lua_body(host, ob)
    # growth that eats the whole surplus: no lx gain, lx decays on x_tau_d, fat pays the shortfall
    dX, dM = host.call("partition.surplusLean", b, 0.1, 12, 1.8, 100.0, D, 1.0)
    assert abs(dX + ob.X / D["x_tau_d"]) < 1e-15
    assert abs(dM - (100.0 - 0.1 * RL) / RF) < 1e-15
    # exactly balanced: still a day with no surplus left
    dX, dM = host.call("partition.surplusLean", b, 0.0, 0, 1.8, 0.0, D, 1.0)
    assert abs(dX + ob.X / D["x_tau_d"]) < 1e-15 and dM == 0
    # a surplus left after growth: lx grows, no decay
    dX, dM = host.call("partition.surplusLean", b, 0.0, 0, 1.8, 400.0, D, 1.0)
    assert dX > 0


def test_labile_lean_is_capped_at_its_share_of_F(host):
    D = _d(host)
    ob = _oracle_body(EXACT, 5.0, 20.0, 150, 0, 1.8, 954.0, 2400.0)
    room = D["x_max_frac"] * ob.F - ob.X
    assert abs(room) < 0.01  # the Bray state at 150 days sits at the cap
    dX, dM = host.call("partition.surplusLean", _lua_body(host, ob), 0.0, 0, 1.8, 954.0, D, 1.0)
    assert abs(dX - max(0.0, room)) < 1e-15
    over = _lua_body(host, ob)
    over["lx"] = D["x_max_frac"] * ob.F + 0.2  # above the cap (F fell): no gain and no decay on a surplus day
    dX, dM = host.call("partition.surplusLean", over, 0.0, 0, 1.8, 954.0, D, 1.0)
    assert dX == 0 and abs(dM - 954.0 / host.K.partition.RHO_FAT) < 1e-15


def test_forbes_and_training(host):
    D = _d(host)
    for fm in (3.5, 9.0, 25.0):
        assert abs(host.call("partition.forbes", fm, D) - D["forbes_c"] / (D["forbes_c"] + fm)) < 1e-15
    assert host.call("partition.training", 5.0, D) == 5.0 / D["S_def"]
    assert host.call("partition.training", 25.0, D) == 1
    P = _copy(host, forbes_c=8.0, S_def=14.0)
    assert host.call("partition.forbes", 9.0, P) == 8.0 / 17.0
    assert host.call("partition.training", 7.0, P) == 0.5


def test_surplus_mass_balance_closes(host):
    D = host.K.strength.DEFAULTS
    b = host.table({"lm": 52.0, "lx": 0.0, "fm": 13.0, "F0": 52.0})
    dX, dM = host.call("partition.surplusLean", b, 0.02, 4.0, 1.6, 300.0, D, 1.0)
    kcal = 0.02 * host.K.partition.RHO_LEAN + dX * host.K.partition.RHO_LEAN + dM * host.K.partition.RHO_FAT
    assert abs(kcal - 300.0) < 1e-9


def test_partition_mass_balance_closes_under_the_clock(host):
    # growth's energy is charged at grow / ts (ruling 13-3); the decay of lx is a mass change with no energy, so
    # these bodies carry no lx on a surplus day, and a deficit day spends it whole
    D = _d(host)
    RL = host.K.partition.RHO_LEAN
    RF = host.K.partition.RHO_FAT
    for ts in TS_GRID:
        for grow, E in ((0.02, 300.0), (0.05, 40.0), (0.0, 954.0)):
            b = host.table({"lm": 52.0, "lx": 0.0, "fm": 13.0})
            dX, dM = host.call("partition.surplusLean", b, grow, 4.0, 1.6, E, D, ts)
            assert abs(grow / ts * RL + dX * RL + dM * RF - E) < 1e-9, (ts, grow, E)
        for fm, lx, S, p, E in ((13.0, 0.0, 12, 1.2, -800.0), (3.5, 0.0, 15, 2.5, -500.0),
                                (25.0, 0.01, 20, 1.2, -1200.0), (3.5, 0.02, 0, 0.6, -900.0)):
            b = host.table({"lm": 60.0, "lx": lx, "fm": fm})
            dF, dX, dM = host.call("partition.deficitLean", b, 0.01, S, p, E, D, ts)
            assert abs(dX + lx) < 1e-15  # lx spent whole, so nothing is left to decay
            assert abs((0.01 / ts + dF + dX) * RL + dM * RF - E) < 1e-9, (ts, fm, lx, E)


def test_contest_leanness_overflows_alperts_ceiling(host):
    # at 3.5 kg fat a 500 kcal deficit overflows the ceiling, so chk4's parity runs the overflow split
    D = _d(host)
    b = host.table({"lm": sm.F_of(so.L_at_s(0.9)), "lx": 0.0, "fm": 3.5})
    dF, dX, dM = host.call("partition.deficitLean", b, 0.0, 15, 2.5, -500.0, D, 1.0)
    assert -dM > host.K.partition.FAT_CEIL_KCAL * 3.5 / host.K.partition.RHO_FAT


def test_pdef_hi_moves_the_deficit_arm_only(host):
    # NR.LeanLossProteinFull moves pdef_hi; the surplus share's ramp is xs_p0 / xs_pspan (ruling 13-37)
    D = _d(host)
    P = _copy(host, pdef_hi=2.4)
    Q = dict(EXACT, pdef_hi=2.4)
    surplus_seen = deficit_moved = 0
    for name, L, fat, S, p, E, tdee in PARTITION_CASES:
        for d, ob in _states(EXACT, L, fat, S, 2.0, E, tdee):
            got = _assert_parity(host, P, Q, ob, S, 2.0, E, tdee, (name, d, "pdef_hi"))
            grow = _oracle_grow_q(EXACT, _clone(EXACT, ob), S, 2.0, E, tdee)
            base = _kernel_arm(host, D, ob, grow, S, 2.0, E, 1.0)
            if E >= 0:
                surplus_seen += 1
                assert tuple(got) == tuple(base), (name, d)
            else:
                deficit_moved += tuple(got) != tuple(base)
    assert surplus_seen > 0 and deficit_moved > 0


DECOY = {
    # keys sharing a point-T value with a key the arm reads, moved apart (and P.ts, which the arms never read:
    # the clock is their argument); the arm must still match the unmoved oracle
    "surplus": {"pdef_lo": 0.6, "pdef_hi": 2.2, "nov_p0": 1.2, "nov_pspan": 0.5, "wT": 0.2, "wP": 0.3,
                "prot_floor": 0.25, "incidental": 0.2, "fMinShare": 0.3, "perfectE": 0.2, "surplus_full": 0.2,
                "ts": 3.0},
    "deficit": {"xs_p0": 0.6, "xs_pspan": 0.5, "nov_p0": 1.2, "nov_pspan": 0.5, "incidental": 0.2,
                "fMinShare": 0.3, "perfectE": 0.2, "surplus_full": 0.2, "x_max_frac": 0.02, "ts": 3.0},
}
# the keys the arms read (xs_p0 and xs_pspan aside: the oracle writes them as literals), moved in both tables
OWN_KEYS = {"forbes_c": 8.0, "wT": 0.5, "S_def": 14.0, "wP": 0.45, "pdef_lo": 0.6, "pdef_hi": 2.4,
            "prot_floor": 0.3, "x_max_frac": 0.03, "x_tau_d": 14.0}


def test_partition_reads_its_own_keys(host):
    D = _d(host)
    for arm, over in DECOY.items():
        P = _copy(host, **over)
        for name, L, fat, S, p, E, tdee in PARTITION_CASES:
            if (E >= 0) != (arm == "surplus"):
                continue
            for d, ob in _states(EXACT, L, fat, S, p, E, tdee):
                _assert_parity(host, P, EXACT, ob, S, p, E, tdee, (arm, name, d))
        if arm == "deficit":
            for d in (40, 150):
                ob = _oracle_body(EXACT, 5.0, 20.0, d, 0, 1.8, 954.0, 2400.0)
                for S, p, E, tdee in CROSS_DEFICITS:
                    _assert_parity(host, P, EXACT, ob, S, p, E, tdee, (arm, "cross", d))
    for key, val in OWN_KEYS.items():
        P = _copy(host, **{key: val})
        Q = dict(EXACT, **{key: val})
        moved = 0
        for name, L, fat, S, p, E, tdee in PARTITION_CASES:
            for d, ob in _states(Q, L, fat, S, p, E, tdee):
                got = _assert_parity(host, P, Q, ob, S, p, E, tdee, (key, name, d))
                grow = _oracle_grow_q(Q, _clone(Q, ob), S, p, E, tdee)
                moved += tuple(got) != tuple(_kernel_arm(host, D, ob, grow, S, p, E, 1.0))
        for d in (40, 150):
            ob = _oracle_body(Q, 5.0, 20.0, d, 0, 1.8, 954.0, 2400.0)
            for S, p, E, tdee in CROSS_DEFICITS + CROSS_SURPLUS:
                got = _assert_parity(host, P, Q, ob, S, p, E, tdee, (key, "cross", d))
                grow = _oracle_grow_q(Q, _clone(Q, ob), S, p, E, tdee)
                moved += tuple(got) != tuple(_kernel_arm(host, D, ob, grow, S, p, E, 1.0))
        assert moved > 0, key


def test_surplus_ramp_reads_the_xs_keys(host):
    # the oracle's literal (p - 0.8) / 0.8 is (p - xs_p0) / xs_pspan: moving them shifts and stretches the ramp
    D = _d(host)
    b = host.table({"lm": 52.0, "lx": 0.0, "fm": 20.0})
    shifted = _copy(host, xs_p0=0.9)
    stretched = _copy(host, xs_pspan=0.4)
    for p in (0.85, 1.0, 1.2, 1.5, 2.0):
        want = host.call("partition.surplusLean", b, 0.0, 0, p - 0.1, 954.0, D, 1.0)
        got = host.call("partition.surplusLean", b, 0.0, 0, p, 954.0, shifted, 1.0)
        assert abs(got[0] - want[0]) < 1e-14 and abs(got[1] - want[1]) < 1e-14, ("xs_p0", p)
        want = host.call("partition.surplusLean", b, 0.0, 0, 0.8 + (p - 0.8) * 2, 954.0, D, 1.0)
        got = host.call("partition.surplusLean", b, 0.0, 0, p, 954.0, stretched, 1.0)
        assert abs(got[0] - want[0]) < 1e-14 and abs(got[1] - want[1]) < 1e-14, ("xs_pspan", p)
    a = host.call("partition.surplusLean", b, 0.0, 0, 1.2, 954.0, shifted, 1.0)
    c = host.call("partition.surplusLean", b, 0.0, 0, 1.2, 954.0, D, 1.0)
    assert a[0] < c[0]
