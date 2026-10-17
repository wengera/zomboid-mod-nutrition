"""The calibrated hunger writer (Plan 15 Task 6; spec section 2.1, items 3, 10a and 10b): K.hungerCurve.

The satiety model's own hunger, h_model, stays underneath (record.satiety.hModel, which the study oracles read); the
HUNGER written to the game is K.hungerCurve.write(h_model, state): a monotone piecewise-linear curve fitted by
tools/fit_hunger_curve.py, the morning circadian dip taken out and the value never falling while unfed, and a dead zone
of 0.02 under each HUNGRY threshold. The kernel cases run on the kernel host; the cadence cases on the server replay
(tools/replay_live.py ServerReplay) through the fit tool's own scenarios.
"""
import math
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
TOOLS = os.path.join(REPO, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

THRESHOLDS = (0.15, 0.25, 0.45, 0.70)    # VANILLA #0508


def knots(host):
    C = host.K.hungerCurve
    return ([C.X[i] for i in range(1, len(C.X) + 1)], [C.Y[i] for i in range(1, len(C.Y) + 1)])


def state(host, hunger, fed=True, circ=1.0):
    return host.table({"hunger": hunger, "fed": fed, "circ": circ})


def write(host, h, hunger, fed=True, circ=1.0):
    return host.call("hungerCurve.write", h, state(host, hunger, fed, circ))


# ---- the curve ----------------------------------------------------------------------------------------------------

def test_the_knots_are_monotone_and_each_level_knot_is_a_vanilla_threshold(host):
    X, Y = knots(host)
    assert X[0] == 0 and X[-1] == 1 and Y[0] == 0 and Y[-1] == 1
    assert all(X[i] < X[i + 1] for i in range(len(X) - 1))
    assert all(Y[i] <= Y[i + 1] for i in range(len(Y) - 1))
    assert tuple(Y[2:6]) == THRESHOLDS
    T = host.K.hungerCurve.THRESHOLDS
    assert tuple(T[i] for i in range(1, len(T) + 1)) == THRESHOLDS
    assert host.K.hungerCurve.DEAD_ZONE == 0.02


def test_the_fitted_knots(host):
    # tools/fit_hunger_curve.py's chosen point (the foot by its rule, the rest by the search), pinned
    X, _ = knots(host)
    assert X[1:6] == [0.097, 0.19, 0.299375, 0.42875, 0.734688]
    assert host.K.hungerCurve.FED_M == host.K.satiety.MEAL_REQ


def test_the_map_is_linear_between_the_knots_and_flat_on_the_foot(host):
    X, Y = knots(host)
    for x, y in zip(X, Y):
        assert host.call("hungerCurve.map", x) == pytest.approx(y)
    assert host.call("hungerCurve.map", -0.1) == 0 and host.call("hungerCurve.map", X[1] / 2) == 0
    assert host.call("hungerCurve.map", 1.5) == 1
    mid = (X[2] + X[3]) / 2
    assert host.call("hungerCurve.map", mid) == pytest.approx((Y[2] + Y[3]) / 2)
    xs = [i / 400.0 for i in range(401)]
    ys = [host.call("hungerCurve.map", x) for x in xs]
    assert all(ys[i] <= ys[i + 1] for i in range(len(ys) - 1))


def test_the_inverse_undoes_the_map_above_the_foot_and_reads_the_foots_end_on_it(host):
    X, _ = knots(host)
    for x in [X[1] + 0.001] + [i / 50.0 for i in range(6, 50)]:
        if x > X[1]:
            assert host.call("hungerCurve.inverse", host.call("hungerCurve.map", x)) == pytest.approx(x)
    assert host.call("hungerCurve.inverse", 0) == pytest.approx(X[1])     # the least sated h_model that reads 0
    assert host.call("hungerCurve.inverse", 1) == 1 and host.call("hungerCurve.inverse", 1.2) == 1   # held at the top


# ---- the dead zone (item 10b) ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("t", THRESHOLDS)
def test_a_level_steps_down_only_past_the_dead_zone(host, t):
    inv = lambda H: host.call("hungerCurve.inverse", H)      # noqa: E731
    above = t + 0.01
    assert write(host, inv(t - 0.005), above) == pytest.approx(t + 0.001)    # held just over the threshold
    assert write(host, inv(t - 0.019), t + 0.001) == pytest.approx(t + 0.001)
    assert write(host, inv(t - 0.021), t + 0.001) == pytest.approx(t - 0.021)    # past the zone: it falls
    assert write(host, inv(t), above) == pytest.approx(t + 0.001)               # at the threshold is under it (#0507)


@pytest.mark.parametrize("t", THRESHOLDS)
def test_the_zone_is_open_at_its_bottom_edge(host, t):
    assert host.call("hungerCurve.hold", t - 0.02, t + 0.01) == t - 0.02      # exactly DEAD_ZONE under: it falls
    assert host.call("hungerCurve.hold", t - 0.0199, t + 0.01) == pytest.approx(t + 0.001)


def test_a_rise_and_a_fall_inside_a_level_are_never_held(host):
    inv = lambda H: host.call("hungerCurve.inverse", H)      # noqa: E731
    assert write(host, inv(0.16), 0.14) == pytest.approx(0.16)                  # the rise shows at once
    assert write(host, inv(0.20), 0.24) == pytest.approx(0.20)                  # a fall inside level 1
    assert write(host, inv(0.10), 0.14) == pytest.approx(0.10)                  # the last write under the threshold
    assert write(host, inv(0.148), 0.1505) == pytest.approx(0.1505)             # never held over the last write


# ---- the fasting bend (item 10a) ------------------------------------------------------------------------------------

def test_unfed_hunger_never_falls_and_the_morning_dip_is_taken_out(host):
    inv = lambda H: host.call("hungerCurve.inverse", H)      # noqa: E731
    h = inv(0.30)
    assert write(host, h, 0.35, fed=False) == pytest.approx(0.35)               # never under the last write
    assert write(host, h * 0.9, 0.0, fed=False, circ=0.9) == pytest.approx(0.30)   # the dip (0.9) taken out
    assert write(host, h * 1.05, 0.0, fed=False, circ=1.05) == pytest.approx(host.call("hungerCurve.map", h * 1.05))
    assert write(host, h * 0.9, 0.0, fed=True, circ=0.9) == pytest.approx(host.call("hungerCurve.map", h * 0.9))
    assert write(host, h, 0.0, fed=False, circ=0) == pytest.approx(0.30)       # a circ that is no positive number


# ---- the writer's caps (K.hybrid.write) -----------------------------------------------------------------------------

def run(host, **kw):
    inp, out, c = host.call("hybrid.input"), host.call("hybrid.output"), host.call("hybrid.defaults")
    for k, v in kw.items():
        inp[k] = v
    host.call("hybrid.write", inp, out, c)
    return out


def test_the_writer_writes_the_curve_capped(host):
    inv = lambda H: host.call("hungerCurve.inverse", H)      # noqa: E731
    assert run(host, mode=1, hungerTarget=inv(0.3)).hunger == pytest.approx(0.3)
    assert run(host, mode=1, hungerTarget=0.95).hunger == pytest.approx(0.69)
    assert run(host, mode=1, hungerTarget=0.95, starving=True).hunger == pytest.approx(
        host.call("hungerCurve.map", 0.95))
    assert run(host, mode=1, hungerTarget=0.2, starving=True).hunger < 0.70                 # the chronic onset
    assert run(host, mode=1, hungerTarget=0.2, starving=True, starveAcute=True).hunger == pytest.approx(0.71)
    assert run(host, mode=2, hungerTarget=0.3).hunger is None


# ---- the cadence on the server replay (tools/fit_hunger_curve.py's scenarios) -----------------------------------------

@pytest.fixture(scope="module")
def fit():
    import fit_hunger_curve as F
    rows3, be = F.replay(F.three_events(), F.DAYS_THREE * F.DAY)
    rowsf, _ = F.replay(F.fast_events(), F.fast_minutes())
    return {"F": F, "three": rows3, "fast": rowsf, "K": be.K}


def H(rows):
    return [r["HUNGER"] for r in rows]


def test_a_satisfying_meal_reads_0_and_the_levels_return_on_vanillas_cadence(fit):
    F = fit["F"]
    meals = [d * F.DAY + m for d in range(1, F.DAYS_THREE) for m in F.MEAL_MIN]
    assert F.deepest(H(fit["three"]), meals) <= 0.02
    s1, s2 = F.shares(H(fit["three"]))
    assert 0.30 <= s1 <= 0.45 and s2 <= 0.08                    # vanilla 0.379 and 0.044 (the review's 38 %)
    t1, t2, t3, tcap, t4 = F.returns(H(fit["fast"]), F.FED_DAYS * F.DAY + F.MEAL_MIN[0])
    assert 3.5 <= t1 <= 4.5                                     # Peckish about 4 h after (vanilla 4.4 h)
    assert 6.0 <= t2 <= 8.5                                     # Hungry 6-8 h after (vanilla 8.0 h)
    assert 15.0 <= t3 <= 19.0                                   # Very Hungry (vanilla 17.0 h)
    assert 33.0 <= tcap <= 36.0                                 # the cap, as vanilla's Starving (34.5 h)
    assert t4 is not None and 0 <= t4 - tcap <= 0.5             # Starving at the acute onset, as the cap comes (fix 1)


def test_the_readings_are_pinned(fit):
    F = fit["F"]
    s1, s2 = F.shares(H(fit["three"]))
    ret = F.returns(H(fit["fast"]), F.FED_DAYS * F.DAY + F.MEAL_MIN[0])
    assert (round(s1, 4), round(s2, 4)) == (0.3576, 0.0312)
    assert [round(t, 2) for t in ret] == [3.78, 8.03, 17.02, 34.48, 34.58]   # Starving 59.48 before fix 1


def test_a_fast_never_lowers_hunger(fit):
    F = fit["F"]
    rows = fit["fast"]
    b = F.FED_DAYS * F.DAY + F.MEAL_MIN[0]
    unfed = next(i for i in range(b, len(rows)) if rows[i]["satiety.M"] < fit["K"].hungerCurve.FED_M)
    w = H(rows)[unfed:]
    assert all(w[i + 1] >= w[i] for i in range(len(w) - 1))
    m = [r["satiety.hModel"] for r in rows[unfed:]]
    assert any(m[i + 1] < m[i] - 1e-3 for i in range(len(m) - 1))   # the model's own value dips: the bend holds it


def test_a_snack_moves_hunger_less_than_a_meal():
    import fit_hunger_curve as F
    b = F.FED_DAYS * F.DAY + F.MEAL_MIN[0]
    drop = {}
    for kcal in (200.0, F.MEAL_KCAL):
        rows, _ = F.replay(F.fast_events(kcal), b + F.AFTER_MIN)
        drop[kcal] = rows[b - 1]["HUNGER"] - min(r["HUNGER"] for r in rows[b:])
    assert 0 < drop[200.0] < drop[F.MEAL_KCAL]


def test_the_mirror_reproduces_the_kernel(fit):
    F = fit["F"]
    C = F.constants(fit["K"])
    X, _ = knots_of(fit["K"])
    for key in ("three", "fast"):
        rows = fit[key]
        t = F.trace(rows, None)["rows"]
        got = F.stage(t[1:], X[1:6], C, rows[0]["HUNGER"])
        assert max(abs(a - r["HUNGER"]) for a, r in zip(got, rows[1:])) < 1e-9


def knots_of(K):
    C = K.hungerCurve
    return [C.X[i] for i in range(1, len(C.X) + 1)], [C.Y[i] for i in range(1, len(C.Y) + 1)]


def test_the_oracles_read_the_models_own_value(fit):
    # record.satiety.hModel is the pre-curve value (the target times the factors), never the written HUNGER: a meal's
    # h_model stays above 0 while the HUNGER written reads 0
    F = fit["F"]
    rows = fit["three"]
    m = F.DAY + F.MEAL_MIN[0] + 30
    assert rows[m]["HUNGER"] == 0 and rows[m]["satiety.hModel"] > 0.05
    assert all(not math.isnan(r["satiety.hModel"]) for r in rows)


# ---- Plan 15 Task 6 fix 1: the acute onset at vanilla's time (30 unfed hours) --------------------------------------

def starving_times(F, rows):
    b = F.FED_DAYS * F.DAY + F.MEAL_MIN[0]
    t_cap = next((i - b) / 60.0 for i in range(b, len(rows)) if rows[i]["HUNGER"] >= 0.69 - 1e-9)
    t_starv = next((i - b) / 60.0 for i in range(b, len(rows)) if rows[i]["HUNGER"] > 0.70)
    t_acute = next((i - b) / 60.0 for i in range(b, len(rows)) if rows[i]["drain.starveAcute"])
    return t_cap, t_starv, t_acute


def test_starving_shows_at_vanillas_time_as_the_curve_reaches_its_cap(fit):
    t_cap, t_starv, t_acute = starving_times(fit["F"], fit["fast"])
    assert abs(t_starv - 34.5) <= 2 and abs(t_acute - 34.5) <= 2          # vanilla's Starving at 34.55 h
    assert 0 <= t_starv - t_cap <= 0.5                                    # H is never parked at 0.69 for long
    assert t_starv == t_acute


@pytest.mark.parametrize("kcal", [200.0, 1300.0])
def test_starving_follows_the_cap_after_a_small_or_a_large_last_meal(kcal):
    import fit_hunger_curve as F
    rows, _ = F.replay(F.fast_events(kcal), F.fast_minutes())
    t_cap, t_starv, t_acute = starving_times(F, rows)
    assert abs(t_starv - t_cap) <= 0.5 and t_starv == t_acute


def test_a_meal_inside_the_acute_state_ends_it_and_the_cap_returns():
    import fit_hunger_curve as F
    b = F.FED_DAYS * F.DAY + F.MEAL_MIN[0]
    m = b + 38 * 60                                                       # 38 h after the breakfast: acute since about 34.6 h
    rows, _ = F.replay(F.fast_events() + [F.meal(m, F.MEAL_KCAL)], m + 30)
    assert rows[m - 1]["drain.starveAcute"] is True and rows[m - 1]["HUNGER"] > 0.70
    assert rows[m]["drain.starveAcute"] is False and rows[m]["drain.starving"] is False
    assert rows[m]["HUNGER"] <= 0.69
