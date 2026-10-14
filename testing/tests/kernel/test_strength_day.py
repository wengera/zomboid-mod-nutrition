"""The strength kernel's day (Plan 13 Task 8; spec sections 4 and 6; rulings 13-2, 13-3 and 13-45).

`K.strength.day` against the tracked oracle's exact day (`strength_model.Body.day`, exact=True) and the
strength-level reference (`strength_level.neural_day`, `perfect_run`): maintenance, exact detraining with its status
term and its grace divided by the biology clock, the remembered peak's decay, the neural factor, the composition of
growth with the lean partition, the floors, and the spec section 12.1 checks the day carries.
"""
import math

import pytest

from . import strength_model as sm
from . import strength_level as sl
from . import strength_oracles as so
from .test_strength_oracle import EXACT_PINS


def _d(host):
    return host.K.strength.DEFAULTS


def _copy(host, **over):
    """A Lua copy of DEFAULTS with the overrides set (the session host is shared, so DEFAULTS is never written)."""
    P = host.rt.table()
    for k, v in _d(host).items():
        P[k] = v
    for k, v in over.items():
        P[k] = v
    return P


def _lua_body_from(host, ob, T=1.0, Tgrace=0):
    return host.table({"lm": ob.F, "F0": ob.F0, "Fc": ob.Fc, "Pk": ob.Pk, "fm": ob.M, "lx": ob.X,
                       "grace": ob.grace, "T": T, "Tgrace": Tgrace})


def _q(ts, **over):
    return dict(sm.POINT_T, exact=True, ts=ts, **over)


def _neural_ref(T, tg, S, ts, Q):
    """strength_level.neural_day under a parameter table Q (bound to neural_day itself at the defaults below)."""
    if S < Q["m"] * Q["Wsat"]:
        tg = tg + 1
    else:
        tg = 0
    if tg > Q["Tgrace_d"] / ts:
        T = 1.0 + (T - 1.0) * math.exp(-ts / (7.0 * Q["tauDownWk"]))
    else:
        T = Q["Tmax"] - (Q["Tmax"] - T) * math.exp(-min(1.0, S / Q["Wsat"]) * ts / (7.0 * Q["tauUpWk"]))
    return T, tg


def _days(host, ob, lb, schedule, ts, P=None, tol=1e-12):
    """Run the oracle body and the kernel body through `schedule` [(days, S, p, E, tdee)], asserting every state
    field after every day; T and Tgrace against strength_level.neural_day (its twin under a moved m). Returns the floors seen (lm, fm)."""
    P = _d(host) if P is None else P
    T, tg = 1.0, 0
    hit_lm = hit_fm = 0
    for n, S, p, E, tdee in schedule:
        for _ in range(n):
            ob.day(S, p, E, tdee)
            host.call("strength.day", lb, S, p, E, tdee, 0.0, P, ts)
            if P["m"] == sm.POINT_T["m"]:
                T, tg = sl.neural_day(T, tg, S, ts)
            else:  # neural_day reads POINT_T's m; under a moved m, its parameterised twin (bound below)
                T, tg = _neural_ref(T, tg, S, ts, dict(sl.LEVEL_MODEL, m=P["m"]))
            assert abs(lb["lm"] - ob.F) < tol
            assert abs(lb["lx"] - ob.X) < tol
            assert abs(lb["fm"] - ob.M) < tol
            assert abs(lb["Pk"] - ob.Pk) < tol
            assert lb["grace"] == ob.grace
            assert abs(lb["T"] - T) < 1e-12
            assert lb["Tgrace"] == tg
            hit_lm += ob.F == 0.35 * ob.F0
            hit_fm += ob.M == 0.5
    return hit_lm, hit_fm


# ---------------------------------------------------------------- parity with the oracle's exact day
@pytest.mark.parametrize("ts", [1.0, 7.0, 30.0])
def test_five_years_of_the_anchor_match_the_oracle(host, ts):
    ob = sm.creation(_q(ts))
    lb = _lua_body_from(host, ob)
    _days(host, ob, lb, [(int(5 * 365 / ts), 20.0, 2.0, 130.0, 2600.0)], ts)


# train, stop (grace, then detraining), retrain below the peak (regain), cut, and a starvation that reaches the fat
# floor; at ts > 1 a day below S_m detrains at grace 1 (the grace divided by ts, amendment 4)
LIFE = ((140, 20.0, 2.0, 260.0, 2600.0), (120, 0.0, 1.2, 0.0, 2400.0), (60, 1.0, 1.6, -300.0, 2400.0),
        (80, 12.0, 1.8, 150.0, 2600.0), (40, 15.0, 2.4, -900.0, 2900.0), (260, 0.0, 0.6, -1500.0, 2200.0))


@pytest.mark.parametrize("ts", [1.0, 2.5, 7.0])
def test_a_life_of_training_detraining_and_starvation_matches_the_oracle(host, ts):
    ob = sm.creation(_q(ts))
    lb = _lua_body_from(host, ob)
    sched = [(max(1, int(n / ts)), S, p, E, tdee) for n, S, p, E, tdee in LIFE]
    _days(host, ob, lb, sched, ts)


def test_the_lean_floor_matches_the_oracle(host):
    # a body built just above the lean floor, starved at contest fat with no protein and no training
    Q = _q(1.0)
    ob = sm.Body(Q, 5.0, 16.5, 0.6)
    ob.F = 0.35 * ob.F0 + 0.05
    ob.Pk = ob.F
    lb = _lua_body_from(host, ob)
    hit_lm, hit_fm = _days(host, ob, lb, [(30, 0.0, 0.0, -2500.0, 2000.0)], 1.0)
    assert hit_lm > 0 and hit_fm > 0


@pytest.mark.parametrize("ts", [1.0, 7.0])
def test_a_trained_body_with_status_detrains_like_the_oracle(host, ts):
    # s > 0 at the stop, so the status term lengthens lam; the peak stays above lm and decays toward it
    Q = _q(ts)
    ob = so.body_at(Q, so.L_at_s(0.7), 11.0)
    ob.Pk = ob.F + 1.5
    lb = _lua_body_from(host, ob)
    _days(host, ob, lb, [(int(200 / ts), 0.5, 1.6, 0.0, 2600.0), (int(100 / ts), 9.0, 1.6, 100.0, 2600.0)], ts)
    assert lb["lm"] < lb["Pk"]


@pytest.mark.parametrize("ts", [1.0, 7.0])
def test_growth_and_detraining_on_one_day_match_the_oracle(host, ts):
    # at m > 1 the maintenance threshold sits above the growth threshold, so a day between them grows and
    # detrains at once: detraining reads the day's opening lm and status, never the grown ones
    P = _copy(host, m=2.0)
    ob = so.body_at(_q(ts, m=2.0), so.L_at_s(0.5), 11.0)
    ob.Pk = ob.F
    lb = _lua_body_from(host, ob)
    lm0 = lb["lm"]
    Sm = host.call("strength.maintainSets", 0.5, P)
    S = 0.5 * (Sm + host.call("strength.threshold", 0.5, P))
    _days(host, ob, lb, [(int(60 / ts), S, 2.0, 260.0, 2600.0)], ts, P)
    b = _lua_body_from(host, ob)
    assert host.call("strength.growth", b, S, 2.0, 260.0, 2600.0, 0.0, P, ts)[0] > 0
    assert host.call("strength.detrain", b, S, host.call("strength.status", b), P, ts) > 0
    assert lb["lm"] != lm0


def test_a_negative_lx_heals_to_zero_like_the_oracle(host):
    # a corrupt store's negative labile lean: the floor writes lx >= 0 on the next day, as the oracle does
    for E in (300.0, 0.0, -400.0):
        ob = sm.creation(_q(1.0))
        ob.X = -0.4
        lb = _lua_body_from(host, ob)
        _days(host, ob, lb, [(3, 12.0, 1.8, E, 2600.0)], 1.0)
        assert lb["lx"] >= 0


DAY_OWN = {"detrain_hl_wk": 9.0, "detrain_status": 0.5, "grace_d": 10, "m": 0.25, "peak_hl_yr": 0.5,
           "regain_hl_wk": 3.0}


def test_the_day_reads_its_own_keys(host):
    # each key the day's steps read, moved in both tables: the kernel follows the oracle and the run moves
    ends = {}
    for key, val in list(DAY_OWN.items()) + [(None, None)]:
        over = {} if key is None else {key: val}
        P = _copy(host, **over)
        ob = so.body_at(_q(1.0, **over), so.L_at_s(0.6), 11.0)
        ob.Pk = ob.F + 2.0
        lb = _lua_body_from(host, ob)
        _days(host, ob, lb, [(60, 0.5, 1.6, 0.0, 2600.0), (60, 6.0, 1.6, 100.0, 2600.0)], 1.0, P)
        ends[key] = (ob.F, ob.Pk)
    for key in DAY_OWN:
        assert ends[key] != ends[None], key


# keys the day never reads that share a point-T or level-block value with one it does (detrain_status and
# peak_hl_yr with perfectP 2.0, tauUpWk with beta... the growth keys are the oracle's), and P.ts: the clock is
# the day's argument
DAY_DECOY = {"perfectP": 3.0, "perfectE": 0.3, "perfectS": 9.0, "incidental": 0.2, "yearsTo10": 2.0, "ts": 3.0,
             "traitShare": 0.3, "xpPerSet": 100, "nov_p0": 1.6, "Tgrace_d": 21, "Wsat": 5.0}


def test_the_day_ignores_decoys(host):
    P = _copy(host, **DAY_DECOY)
    ob = so.body_at(_q(1.0), so.L_at_s(0.6), 11.0)
    ob.Pk = ob.F + 2.0
    lb = _lua_body_from(host, ob)
    _days(host, ob, lb, [(60, 0.5, 1.6, 0.0, 2600.0), (60, 6.0, 1.6, 100.0, 2600.0), (30, 12.0, 2.0, -500.0, 2600.0)],
          1.0, P)


def test_the_floors_read_their_keys(host):
    # the oracle writes 0.35 and 0.5 as literals; the kernel reads fMinShare and fmMin
    P = _copy(host, fMinShare=0.9, fmMin=4.0)
    F0 = sm.F_of(5.0)
    b = host.table({"lm": F0 * 0.9 + 0.01, "F0": F0, "Fc": sm.F_of(16.5), "Pk": F0, "fm": 4.02, "lx": 0.0,
                    "grace": 0, "T": 1.0, "Tgrace": 0})
    for _ in range(10):
        host.call("strength.day", b, 0.0, 0.0, -2500.0, 2000.0, 0.0, P, 1.0)
    assert b["lm"] == 0.9 * F0 and b["fm"] == 4.0 and b["lx"] == 0


def test_the_day_returns_its_composed_changes(host):
    D = _d(host)
    ob = so.body_at(_q(1.0), so.L_at_s(0.4), 12.0)
    ob.Pk = ob.F
    for S, p, E in ((12.0, 2.3, -1200.0), (15.0, 2.0, 290.0), (0.0, 1.8, 954.0)):
        b = _lua_body_from(host, ob)
        lm, lx, fm = b["lm"], b["lx"], b["fm"]
        dF, dX, dM = host.call("strength.day", b, S, p, E, 3000.0, 0.0, D, 1.0)
        assert abs(b["lm"] - (lm + dF)) < 1e-12 and abs(b["lx"] - (lx + dX)) < 1e-12
        assert abs(b["fm"] - (fm + dM)) < 1e-12


def test_alcohol_reaches_the_day(host):
    D = _d(host)
    ob = sm.creation(_q(1.0))
    sober = _lua_body_from(host, ob)
    drunk = _lua_body_from(host, ob)
    host.call("strength.day", sober, 20.0, 2.0, 260.0, 2600.0, 0.0, D, 1.0)
    host.call("strength.day", drunk, 20.0, 2.0, 260.0, 2600.0, 1.2, D, 1.0)
    gs = sober["lm"] - ob.F
    gd = drunk["lm"] - ob.F
    assert gs > 0 and abs(gd - host.K.partition.G_ALC * gs) < 1e-12


@pytest.mark.parametrize("tdee", [0.0, -50.0, float("nan")])
def test_a_zero_tdee_reads_the_gate_at_balance(host, tdee):
    # amendment 3: fe's surplus share divides by tdee; the day reads tdee <= 0 (or NaN) as the gate at balance
    D = _d(host)
    ob = so.body_at(_q(1.0), so.L_at_s(0.5), 11.0)
    ob.Pk = ob.F
    for E in (0.0, 200.0, -200.0):
        b = _lua_body_from(host, ob)
        ref = _lua_body_from(host, ob)
        host.call("strength.day", b, 15.0, 2.0, E, tdee, 0.0, D, 1.0)
        host.call("strength.day", ref, 15.0, 2.0, min(E, 0.0), 2600.0, 0.0, D, 1.0)
        for k in ("lm", "Pk", "T"):
            assert math.isfinite(b[k]) and b[k] == ref[k], (tdee, E, k)
        assert math.isfinite(b["fm"]) and math.isfinite(b["lx"])
    # the gate at balance at s = 0.5 is fbal (0.75 here), so a surplus with tdee 0 grows less than with a real tdee
    b = _lua_body_from(host, ob)
    full = _lua_body_from(host, ob)
    host.call("strength.day", b, 15.0, 2.0, 200.0, tdee, 0.0, D, 1.0)
    host.call("strength.day", full, 15.0, 2.0, 200.0, 2600.0, 0.0, D, 1.0)
    assert ob.F < b["lm"] < full["lm"]


# ---------------------------------------------------------------- maintenance, detraining, the peak
def test_maintenance_is_m_times_the_threshold(host):
    D = _d(host)
    for s in (0.0, 0.3, 0.9, 1.0):
        want = D["m"] * D["Sg0"] * math.exp(D["beta"] * s)
        assert abs(host.call("strength.maintainSets", s, D) - want) < 1e-15
    P = _copy(host, m=0.5)
    assert host.call("strength.maintainSets", 0.0, P) == 0.5 * D["Sg0"]


@pytest.mark.parametrize("ts", [1.0, 7.0])
def test_detraining_one_day_factor(host, ts):
    # grace past, S = 0: lm - F0 falls by exactly exp(-lam * ts / 7) in one day, lam carrying the status term
    D = _d(host)
    F0 = sm.F_of(5.0)
    Fc = sm.F_of(16.5)
    for lm in (F0 + 2.0, F0 + 9.0):
        b = host.table({"lm": lm, "F0": F0, "Fc": Fc, "Pk": lm, "fm": 11.0, "lx": 0.0, "grace": D["grace_d"],
                        "T": 1.0, "Tgrace": 0})
        s = (lm - F0) / (Fc - F0)
        lam = math.log(2) / (D["detrain_hl_wk"] * (1 + D["detrain_status"] * s))
        host.call("strength.day", b, 0.0, 0.0, 0.0, 2600.0, 0.0, D, ts)
        assert b["grace"] == D["grace_d"] + 1
        assert abs((b["lm"] - F0) / (lm - F0) - math.exp(-lam * ts / 7)) < 1e-12
        # the direct call: the same factor, and a day at or above S_m resets the counter and detrains nothing
        b2 = host.table({"lm": lm, "F0": F0, "grace": D["grace_d"]})
        detr = host.call("strength.detrain", b2, 0.0, s, D, ts)
        assert abs(detr - (lm - F0) * (1 - math.exp(-lam * ts / 7))) < 1e-12
        Sm = host.call("strength.maintainSets", s, D)
        b3 = host.table({"lm": lm, "F0": F0, "grace": 40})
        assert host.call("strength.detrain", b3, Sm, s, D, ts) == 0 and b3["grace"] == 0


def test_detraining_scales_with_the_shortfall_and_stops_at_F0(host):
    D = _d(host)
    F0 = sm.F_of(5.0)
    Sm = host.call("strength.maintainSets", 0.0, D)
    b = host.table({"lm": F0 + 3.0, "F0": F0, "grace": 99})
    lam = math.log(2) / D["detrain_hl_wk"]
    detr = host.call("strength.detrain", b, Sm / 2, 0.0, D, 1.0)
    assert abs(detr - 3.0 * (1 - math.exp(-lam * 0.5 / 7))) < 1e-12
    at = host.table({"lm": F0, "F0": F0, "grace": 99})
    assert host.call("strength.detrain", at, 0.0, 0.0, D, 1.0) == 0 and at["grace"] == 100


def test_the_grace_is_divided_by_the_clock(host):
    # at ts = 7 the 14-day grace is 2 days: the third day below S_m detrains; at ts = 1 the fifteenth does
    D = _d(host)
    F0 = sm.F_of(5.0)
    for ts, first in ((1.0, 15), (7.0, 3), (28.0, 1)):
        b = host.table({"lm": F0 + 3.0, "F0": F0, "grace": 0})
        days = []
        for day in range(1, 20):
            if host.call("strength.detrain", b, 0.0, 0.0, D, ts) > 0:
                days.append(day)
        assert days[0] == first, ts


def test_detraining_half_life_is_six_weeks_after_a_fourteen_day_grace(host):
    # spec section 12.1, detrain_status 0 for the novice reading (S2001's population)
    P = _copy(host, detrain_status=0.0)
    F0 = sm.F_of(5.0)
    Fc = sm.F_of(16.5)
    b = host.table({"lm": F0 + 4.0, "F0": F0, "Fc": Fc, "Pk": F0 + 4.0, "fm": 11.0, "lx": 0.0, "grace": 0,
                    "T": 1.0, "Tgrace": 0})
    for _ in range(int(P["grace_d"])):
        host.call("strength.day", b, 0.0, 0.0, 0.0, 2600.0, 0.0, P, 1.0)
    assert b["lm"] == F0 + 4.0  # the grace: 14 days below S_m and nothing lost
    for _ in range(int(7 * P["detrain_hl_wk"])):
        host.call("strength.day", b, 0.0, 0.0, 0.0, 2600.0, 0.0, P, 1.0)
    assert abs((b["lm"] - F0) / 4.0 - 0.5) < 1e-12
    assert P["detrain_hl_wk"] == 6.0 and P["grace_d"] == 14


@pytest.mark.parametrize("ts", [1.0, 7.0])
def test_the_peak_holds_the_max_and_decays_toward_lm(host, ts):
    D = _d(host)
    dec = math.log(2) / (D["peak_hl_yr"] * 365)
    b = host.table({"lm": 60.0, "Pk": 64.0})
    host.call("strength.peakStep", b, D, ts)
    assert abs(b["Pk"] - (60.0 + 4.0 * math.exp(-dec * ts))) < 1e-12
    up = host.table({"lm": 66.0, "Pk": 64.0})
    host.call("strength.peakStep", up, D, ts)
    assert up["Pk"] == 66.0
    # two years of biology halve the gap: 730 days at ts 1, 730 / ts days at ts (7 divides 728, so 104 weeks)
    h = host.table({"lm": 60.0, "Pk": 64.0})
    n = int(2 * 365 / ts)
    for _ in range(n):
        host.call("strength.peakStep", h, D, ts)
    assert abs((h["Pk"] - 60.0) / 4.0 - 0.5 ** (n * ts / 730)) < 1e-12
    if ts == 1.0:
        assert abs((h["Pk"] - 60.0) / 4.0 - 0.5) < 1e-12


# ---------------------------------------------------------------- the neural factor (ruling 13-45)
NEURAL_SCHEDULE = ((70, 20.0), (140, 0.0), (30, 3.0), (70, 20.0))


@pytest.mark.parametrize("ts", [1.0, 7.0])
def test_neural_matches_the_reference_day_by_day(host, ts):
    D = _d(host)
    b = host.table({"T": 1.0, "Tgrace": 0})
    T, tg = 1.0, 0
    phases = set()
    for n, S in NEURAL_SCHEDULE:
        for _ in range(n):
            before = T
            T, tg = sl.neural_day(T, tg, S, ts)
            host.call("strength.neural", b, S, D, ts)
            assert abs(b["T"] - T) < 1e-12 and b["Tgrace"] == tg
            if S == 0.0:
                phases.add("hold" if T == before else "decay")
            elif S == 3.0:
                phases.add("partial")
    assert phases == {"hold", "decay", "partial"}


def test_neural_reference_binding():
    # _neural_ref is strength_level.neural_day under a parameter table
    Q = dict(sl.LEVEL_MODEL, m=sm.POINT_T["m"])
    for T, tg, S, ts in ((1.0, 0, 20.0, 1.0), (1.05, 21, 0.0, 1.0), (1.05, 2, 0.0, 7.0), (1.02, 4, 3.0, 7.0),
                         (1.03, 0, 1.6, 1.0)):
        assert _neural_ref(T, tg, S, ts, Q) == sl.neural_day(T, tg, S, ts)


NEURAL_OWN = {"m": 0.5, "Wsat": 4.0, "Tgrace_d": 10, "Tmax": 1.2, "tauUpWk": 2.0, "tauDownWk": 6.0}
# keys neural never reads that share a value with one it does (tauUpWk 3.0 with beta, tauDownWk 12 with Sref and
# Smax1, Tgrace_d 21 with none but grace_d's role, Wsat with S_def's half), and P.ts
NEURAL_DECOY = {"beta": 2.0, "Sref": 10.0, "Smax1": 9.0, "grace_d": 7, "S_def": 8.0, "detrain_hl_wk": 4.0,
                "perfectS": 9.0, "ts": 3.0, "Sg0": 1.0, "fbal_drop": 0.2}


@pytest.mark.parametrize("ts", [1.0, 7.0])
def test_neural_reads_its_own_keys(host, ts):
    base = dict(sl.LEVEL_MODEL, m=sm.POINT_T["m"])
    for over in [NEURAL_DECOY] + [{k: v} for k, v in NEURAL_OWN.items()]:
        P = _copy(host, **over)
        Q = dict(base)
        for k, v in over.items():
            if k in NEURAL_OWN:
                Q[k] = v
        b = host.table({"T": 1.0, "Tgrace": 0})
        T, tg = 1.0, 0
        moved = False
        Td, tgd = 1.0, 0
        for n, S in NEURAL_SCHEDULE + ((60, 1.8), (40, 2.2)):
            for _ in range(max(1, int(n / ts))):
                T, tg = _neural_ref(T, tg, S, ts, Q)
                Td, tgd = _neural_ref(Td, tgd, S, ts, base)
                host.call("strength.neural", b, S, P, ts)
                assert abs(b["T"] - T) < 1e-12 and b["Tgrace"] == tg, over
                moved = moved or T != Td or tg != tgd
        assert moved == (over is not NEURAL_DECOY), over


# ---------------------------------------------------------------- spec section 12.1
def test_the_growth_anchor_bio_level_15_at_5_years(host):
    # 20 sets, full gates (p = 2.0, E = 0.10 tdee: f_e = 1 at every status, ruling 13-21), the average character
    D = _d(host)
    ob = sm.creation(_q(1.0))
    b = _lua_body_from(host, ob)
    for _ in range(5 * 365):
        host.call("strength.day", b, 20.0, 2.0, 260.0, 2600.0, 0.0, D, 1.0)
    assert abs(host.call("strength.bioLevel", b["lm"], D) - 15.0) < 0.02


def test_the_strength_level_is_10_at_4_years_and_matches_the_reference(host):
    D = _d(host)
    lm = sl.LEVEL_MODEL
    F, F0, Fc, Pk = sl.trait_start("none")
    b = host.table({"lm": F, "F0": F0, "Fc": Fc, "Pk": Pk, "fm": sl.FAT_KG, "lx": 0.0, "grace": 0, "T": 1.0,
                    "Tgrace": 0})
    ref = sl.perfect_run("none", 3650)
    marks = (28, 70, 182, 365, 730, 1460, 3650)
    for day in range(1, 3651):
        host.call("strength.day", b, lm["perfectS"], lm["perfectP"], lm["perfectE"] * sl.TDEE, sl.TDEE, 0.0, D, 1.0)
        if day in marks:
            got = host.call("strength.level", b["lm"], 1.0, b["T"], D)
            assert abs(got - ref[day - 1]) < 1e-9, day
            if day == 1460:
                assert abs(got - 10.0) < 0.02


def _adv(host, s, fat, S, p, E, days=56, tdee=2900.0):
    D = _d(host)
    ob = so.body_at(_q(1.0), so.L_at_s(s), fat)
    ob.Pk = ob.F
    b = _lua_body_from(host, ob)
    for _ in range(days):
        host.call("strength.day", b, S, p, E, tdee, 0.0, D, 1.0)
    return b["lm"] - ob.F, b["lx"] - ob.X, b["fm"] - ob.M, ob.F


def test_the_status_gate_at_s_0_9_over_8_weeks(host):
    bal = _adv(host, 0.9, 9.0, 15, 2.0, 0.0)
    assert 0 <= 100 * bal[0] / bal[3] < 0.5
    sur = _adv(host, 0.9, 9.0, 15, 2.0, 0.10 * 2900)
    assert 0 < sur[0] <= 2 * bal[0]
    assert 100 * sur[0] / sur[3] < 1.0
    assert sur[2] / (sur[0] + sur[1] + sur[2]) >= 0.5
    cut = _adv(host, 0.9, 3.5, 15, 2.5, -500.0)
    assert cut[0] <= 0
    # against the oracle's exact pins
    assert abs(100 * bal[0] / bal[3] - EXACT_PINS["chk1_s09_bal_dF_pct"]) < 1e-9
    assert abs(sur[0] / bal[0] - EXACT_PINS["chk2_s09_surplus_over_bal"]) < 1e-9
    assert abs(cut[0] - EXACT_PINS["chk4_s09_contest_minus500"]) < 1e-9


def test_retraining_block_two_over_block_one_is_the_pinned_ratio(host):
    # Räntilä, strength_oracles._rantila's protocol: novices, 10 wk on, 10 wk off, 10 wk on (9 sets, 1.6 g/kg,
    # balance); the ratio lies in the oracle's band and equals Task 2's exact pin (ruling 13-22)
    D = _d(host)
    ob = sm.creation(_q(1.0))
    b = _lua_body_from(host, ob)
    F0 = b["lm"]

    def run(n, S):
        for _ in range(n):
            host.call("strength.day", b, S, 1.6, 0.0, 2600.0, 0.0, D, 1.0)

    run(70, 9)
    g1 = b["lm"] - F0
    run(70, 0)
    Fd = b["lm"]
    run(70, 9)
    ratio = (b["lm"] - Fd) / g1
    assert 0.80 <= ratio <= 1.25
    assert abs(ratio - EXACT_PINS["rantila_block2_over_1"]) < 1e-9


@pytest.mark.parametrize("tdee", [0.0, -50.0, float("nan")])
def test_a_zero_tdee_partitions_the_real_balance(host, tdee):
    # the guard reads the gate at balance, but the partition arms take the day's real E
    D = _d(host)
    ob = so.body_at(_q(1.0), so.L_at_s(0.5), 11.0)
    ob.Pk = ob.F
    ob.X = 0.3
    for E in (200.0, 0.0, -200.0):
        b0 = _lua_body_from(host, ob)
        grow = max(host.call("strength.growth", b0, 15.0, 2.0, min(E, 0.0), 2600.0, 0.0, D, 1.0))
        if E >= 0:
            dX, dM = host.call("partition.surplusLean", b0, grow, 15.0, 2.0, E, D, 1.0)
        else:
            _, dX, dM = host.call("partition.deficitLean", b0, grow, 15.0, 2.0, E, D, 1.0)
        b = _lua_body_from(host, ob)
        host.call("strength.day", b, 15.0, 2.0, E, tdee, 0.0, D, 1.0)
        assert b["fm"] == max(ob.M + dM, D["fmMin"]) and b["lx"] == max(ob.X + dX, 0.0), (tdee, E)


def test_neural_threshold_is_strictly_below_m_wsat(host):
    D = _d(host)
    at = D["m"] * D["Wsat"]
    b = host.table({"T": 1.05, "Tgrace": 30})
    host.call("strength.neural", b, at, D, 1.0)
    assert b["Tgrace"] == 0 and b["T"] > 1.05
    T, tg = sl.neural_day(1.05, 30, at, 1.0)
    assert b["T"] == T and b["Tgrace"] == tg


# ---------------------------------------------------------------- Task 11c: regain integrated exactly (Task 11 review I-2)
REGAIN_GRID = [(ts, hl) for ts in (1.0, 2.0, 30.0) for hl in (1.0, 6.0)]


def _far_below_the_peak(Q):
    """A body far below a held peak: lean at bio 6, the peak at bio 14, the set point at bio 5."""
    return sm.Body(Q, 6.0, 16.5, 13.0, F0L=5.0, peakL=14.0)


@pytest.mark.parametrize("ts, hl", REGAIN_GRID)
def test_regain_far_below_the_peak_matches_the_oracle(host, ts, hl):
    # the regain arm wins every early day here; at ts 30 and a 1-week half-life the Euler form's daily fraction
    # was 2.97, and the exact oracle's day must still be matched to 1e-12 on every state field
    P = _copy(host, regain_hl_wk=hl)
    ob = _far_below_the_peak(_q(ts, regain_hl_wk=hl))
    lb = _lua_body_from(host, ob)
    _days(host, ob, lb, [(max(1, int(60 / ts)), 20.0, 2.0, 260.0, 2600.0),
                         (max(1, int(30 / ts)), 12.0, 1.6, -300.0, 2600.0)], ts, P)


def _regain_days_stay_under_the_peak(host, P, ts):
    """Train the body far below its peak for 40 days and return, over the regain days (the regain arm above the
    growth arm, read before the day), the worst excess of lm over the day's opening Pk, and their count."""
    ob = _far_below_the_peak(_q(ts))
    lb = _lua_body_from(host, ob)
    worst = -math.inf
    regain_days = 0
    for _ in range(40):
        Pk = lb["Pk"]
        grow, regain = host.call("strength.growth", lb, 20.0, 2.0, 260.0, 2600.0, 0.0, P, ts)
        host.call("strength.day", lb, 20.0, 2.0, 260.0, 2600.0, 0.0, P, ts)
        if regain > grow:
            regain_days += 1
            worst = max(worst, lb["lm"] - Pk)
    return worst, regain_days


@pytest.mark.parametrize("ts, hl", REGAIN_GRID)
def test_lm_never_passes_the_peak_on_a_regain_day(host, ts, hl):
    worst, regain_days = _regain_days_stay_under_the_peak(host, _copy(host, regain_hl_wk=hl), ts)
    assert regain_days > 0 and worst <= 0.0, (ts, hl, worst)


EULER_GROWTH = """
local K = ...
return function(body, S, p, E, tdee, alcGkg, P, ts)
    local s = K.strength.status(body)
    local G = K.strength.signal(S, s, P)
    local gates = K.strength.fp(p, P) * K.strength.fe(E, s, p, tdee, P) * K.partition.gAlc(alcGkg)
    local grow = K.max(0, P.k * (body.Fc - body.lm) * G * gates / 7) * ts
    local regain = 0
    if body.lm < body.Pk then
        regain = math.log(2) / P.regain_hl_wk * (body.Pk - body.lm) * K.min(1, G) * gates / 7 * ts
    end
    return grow, regain
end
"""


def test_the_euler_regain_fails_the_peak_bound(host):
    # the mutation: the pre-Task 11c Euler regain arm (ts applied after the step) fails the bound at ts 30 and a
    # 1-week half-life, the exact arm's own test above
    euler = host.rt.execute(EULER_GROWTH, host.K)
    exact = host.K.strength["growth"]
    host.K.strength["growth"] = euler
    try:
        worst, _ = _regain_days_stay_under_the_peak(host, _copy(host, regain_hl_wk=1.0), 30.0)
    finally:
        host.K.strength["growth"] = exact
    assert worst > 1.0
