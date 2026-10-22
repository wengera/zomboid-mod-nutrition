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
    assert X[1:6] == [0.097, 0.21125, 0.289531, 0.420782, 0.6825]     # X[3] 0.19 before Task 6c; 0.097, 0.210312 before Task 14b's re-fit; 0.099, 0.214688, 0.299375, 0.42875, 0.734688 before Plan 16 Task 4b's re-fit on both sleep settings
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

def _fit(config):
    import fit_hunger_curve as F
    rows3, be = F.replay(F.three_events(0, config), F.DAYS_THREE * F.DAY, config=config)
    rowsf, _ = F.replay(F.fast_events(F.MEAL_KCAL, config), F.fast_minutes(), config=config)
    return {"F": F, "three": rows3, "fast": rowsf, "K": be.K, "config": config}


@pytest.fixture(scope="module")
def fit():
    # the shipped configuration (sleep off, the server default since Plan 16 Task 4: no daily rhythm)
    return _fit("off")


@pytest.fixture(scope="module")
def fit_on():
    # sleep on: asleep 23:00 to 07:00, the rhythm on the body clock (Plan 16 Task 4), through the real code path
    return _fit("on")


@pytest.fixture(scope="module", params=["off", "on"])
def fit_any(request, fit, fit_on):
    return fit if request.param == "off" else fit_on


def H(rows):
    return [r["HUNGER"] for r in rows]


def test_a_satisfying_meal_reads_0_and_the_levels_return_on_vanillas_cadence(fit_any):
    F = fit_any["F"]
    meals = [d * F.DAY + m for d in range(1, F.DAYS_THREE) for m in F.MEAL_MIN]
    assert F.deepest(H(fit_any["three"]), meals) <= 0.02
    s1, s2 = F.shares(H(fit_any["three"]))
    # vanilla 0.379 and 0.044 (the review's 38 %); Task 6c trades the level-1 share (0.358 before) for each meal's
    # return: vanilla's share is mostly its breakfast can's carry-over, which the satiety model has none of
    assert 0.18 <= s1 <= 0.30 and s2 <= 0.08
    t1, t2, t3, tcap, t4 = F.returns(H(fit_any["fast"]), F.FED_DAYS * F.DAY + F.MEAL_MIN[0])
    # Peckish about 4 h after (vanilla 4.4 h; 3.78 before 6c). Plan 16 Task 4b: the joint fit reads 3.88 h with sleep
    # off (the breakfast and share terms pull the Peckish knot under the fast's own target), so the band opens to 3.8
    assert 3.8 <= t1 <= 4.8
    assert 6.0 <= t2 <= 8.5                                     # Hungry 6-8 h after (vanilla 8.0 h; 9.15 sleep off before 4b)
    assert 15.0 <= t3 <= 19.0                                   # Very Hungry (vanilla 17.0 h)
    assert 33.0 <= tcap <= 36.0                                 # the cap, as vanilla's Starving (34.5 h)
    # Starving at the acute onset, as the cap comes (fix 1); with sleep on the joint fit's cap comes 1.45 h before the
    # onset (Plan 16 Task 4b: the cap falls at 16:38 on the body clock, where the circadian factor is over 1, an
    # inference), so H holds at 0.69 that long
    parked = 0.5 if fit_any["config"] == "off" else 1.5
    assert t4 is not None and 0 <= t4 - tcap <= parked


@pytest.mark.parametrize("config, share, ret", [
    # (0.3576, 0.0312) before Task 6c; (0.2115, 0.0312) before Task 14b; (0.2302, 0.0312) and [4.37, 8.03, 17.02, 34.48,
    # 34.58] on the world-clock rhythm before Plan 16 Task 4b. Starving 59.48 before fix 1; t1 3.78 before 6c
    ("off", (0.2417, 0.0312), [3.88, 8.1, 17.33, 34.48, 34.58]),
    ("on", (0.224, 0.0312), [4.4, 7.83, 16.83, 33.13, 34.58]),
])
def test_the_readings_are_pinned(fit, fit_on, config, share, ret):
    f = fit if config == "off" else fit_on
    F = f["F"]
    s1, s2 = F.shares(H(f["three"]))
    got = F.returns(H(f["fast"]), F.FED_DAYS * F.DAY + F.MEAL_MIN[0])
    assert (round(s1, 4), round(s2, 4)) == share
    assert [round(t, 2) for t in got] == ret


# ---- Plan 15 Task 6c: every meal's return to Peckish -----------------------------------------------------------------

def test_vanillas_three_can_day_returns_each_meal_to_peckish():
    # tools/vanilla_model.py at DayLength 4: the breakfast can (0.24) is short of the night's rise, so it carries hunger
    # and returns at 1.17 h; lunch carries 0.016 (4.25 h); dinner lands on the floor and the Well Fed pause holds it (5 h)
    import fit_hunger_curve as F
    V = F.vanilla()
    assert {k: [round(t, 2) for t in v] for k, v in V["meals"].items()} == {
        "breakfast": [1.17] * 3, "lunch": [4.25] * 3, "dinner": [5.0] * 3}


@pytest.mark.parametrize("config, pinned", [
    # the guide's water. Task 14b's re-fit (the liquid lane slowed only by drink-borne kcal) read 4.37, 3.98 and 3.83 on
    # the world-clock rhythm (4.33, 4.15 and 3.98 before it); Plan 16 Task 4b re-fits on both sleep settings
    ("off", {"breakfast": [3.88] * 3, "lunch": [4.18] * 3, "dinner": [4.07] * 3}),
    ("on", {"breakfast": [4.4] * 3, "lunch": [4.02] * 3, "dinner": [3.85] * 3}),
])
def test_each_meal_returns_to_peckish_nearer_vanilla_than_the_task_6_curve(fit, fit_on, config, pinned):
    f = fit if config == "off" else fit_on
    F = f["F"]
    mr = F.meal_returns(H(f["three"]))
    got = {k: [round(t, 2) for t, _ in v] for k, v in mr.items()}
    assert got == pinned
    assert not any(c for v in mr.values() for _, c in v)
    # before Task 6c (X[3] 0.19): breakfast 3.78, lunch 3.28 and dinner 2.93 h, against vanilla's 4.25 and 5.0 h
    assert got["lunch"][0] > 3.28 + 0.5 and got["dinner"][0] > 2.93 + 0.5
    assert 3.8 <= got["lunch"][0] <= 4.7 and 3.5 <= got["dinner"][0] <= 5.0


def test_the_fit_scores_each_meal_on_both_water_schedules():
    # the loss carries the three meal terms (Task 6c), each the mean log ratio over days 1-3 of the two water
    # schedules' mean return; a mutated meal reading moves the loss
    import fit_hunger_curve as F
    traces, be = F.traces_of("off")
    C, V = F.constants(be.K), F.vanilla()
    r = F.read_config(F.shipped(be.K), traces, C, V)
    assert set(F.MEALS) <= set(r["miss"])
    for j, m in enumerate(F.MEALS):
        a, b = r["mealsByWater"]["guide"][m], r["mealsByWater"]["shifted"][m]
        assert r["meals"][m] == [pytest.approx((x + y) / 2) for x, y in zip(a, b)]
        logs = [math.log(t / v) for t, v in zip(r["meals"][m], V["meals"][m])]
        assert r["miss"][m] == pytest.approx(F.W_MEAL[j] * sum(logs) / len(logs))
    assert r["loss"] == pytest.approx(sum(v * v for v in r["miss"].values()))
    V2 = dict(V, meals=dict(V["meals"], dinner=[10.0] * 3))
    assert F.read_config(F.shipped(be.K), traces, C, V2)["loss"] > r["loss"] + 0.1


def test_the_fit_scores_both_sleep_settings_weighted_sleep_off_first(monkeypatch):
    # Plan 16 Task 4b: the joint loss is each configuration's loss weighted by W_CONFIG (sleep off 2, sleep on 1, a game
    # choice) over the weights' sum, each configuration on its own replays; a moved weight moves the loss
    import fit_hunger_curve as F
    traces, be = F.all_traces()
    C, V = F.constants(be.K), F.vanilla()
    knots = F.shipped(be.K)
    r = F.read(knots, traces, C, V)
    off, on = r["configs"]["off"], r["configs"]["on"]
    assert r["loss"] == pytest.approx((2.0 * off["loss"] + on["loss"]) / 3.0)
    assert off["loss"] == pytest.approx(F.read_config(knots, traces["off"], C, V)["loss"])
    assert off["returns"] != on["returns"]                               # two replays, not one read twice
    assert F.W_CONFIG == {"off": 2.0, "on": 1.0} and F.CONFIGS == ("off", "on") and F.SHIPPED_CONFIG == "off"
    monkeypatch.setattr(F, "W_CONFIG", {"off": 1.0, "on": 1.0})
    assert F.read(knots, traces, C, V)["loss"] == pytest.approx((off["loss"] + on["loss"]) / 2.0)
    assert F.foot(traces) == 0.097                                       # the foot over both settings (sleep on's dinner)


def test_the_fits_replays_run_the_shipped_rhythm_with_no_overlay():
    # Plan 16 Task 4b: sleep off has no body clock (the circadian factor 1); sleep on seeds the body clock at the world
    # hour (07:00) and each 23:00-07:00 night resets it to 07:00 plus the gap at the bout's close; no WORLD_CLOCK
    import inspect
    import fit_hunger_curve as F
    assert "WORLD_CLOCK" not in inspect.getsource(F)
    n = 2 * F.DAY
    rows, _ = F.replay(F.three_events(0, "off"), n, config="off")
    assert all(r["acute.bodyOn"] is False and r.get("acute.bodyHour") is None for r in rows)
    rows, _ = F.replay(F.three_events(0, "on"), n, config="on")
    assert rows[0]["acute.bodyOn"] is True and rows[0]["acute.bodyHour"] == pytest.approx(7.0, abs=0.02)
    t = F.trace(rows, None)["rows"]
    assert t[600]["body"] == pytest.approx(math.fmod(rows[600]["age"] + F.HOUR_OFFSET, 24.0), abs=0.02)
    woke = F.DAY + 15                                                    # 07:15, after the night's bout closed
    assert rows[woke]["acute.bodyHour"] == pytest.approx(7.25, abs=0.02)
    with pytest.raises(ValueError):
        F.replay([], 10, config="maybe")


def test_the_two_water_schedules_differ_and_the_weights_are_the_artifacts():
    # Task 6c review F3: the shifted schedule is a real second replay (dinner 4.07 h on the guide water, 3.92 h an hour
    # later with sleep off since Plan 16 Task 4b's re-fit; 3.83 and 3.53 on the world-clock rhythm after Task 14b), and
    # the weights and the shift are the ones fit-hunger-curve-20261018 was fitted with (Task 6c's, unchanged, and Plan
    # 16 Task 4b's configuration weights)
    import json
    import fit_hunger_curve as F
    rows, _ = F.replay(F.three_events(), F.DAYS_THREE * F.DAY)
    rows_s, _ = F.replay(F.three_events(F.WATER_SHIFT), F.DAYS_THREE * F.DAY)
    guide = F.meal_returns(H(rows))["dinner"][1][0]
    shifted = F.meal_returns(H(rows_s))["dinner"][1][0]
    assert (round(guide, 2), round(shifted, 2)) == (4.07, 3.92)
    with open(os.path.join(REPO, "testing", "artifacts", "fit-hunger-curve-20261018", "fit-compact.json"),
              encoding="utf-8") as fh:
        art = json.load(fh)
    w = art["search"]["weights"]
    assert w["meals"] == dict(zip(F.MEALS, F.W_MEAL)) and w["meals"]["breakfast"] == F.W_CARRY
    assert w["shares"] == F.W_SHARE == F.W_CARRY and w["others"] == 1.0
    assert w["configs"] == F.W_CONFIG
    assert art["scenarios"]["WATER_SHIFT"] == F.WATER_SHIFT
    assert art["scenarios"]["CONFIGS"] == list(F.CONFIGS) and art["scenarios"]["SLEEP_MIN"] == F.SLEEP_MIN
    assert F.W_CARRY == 0.5 and F.WATER_SHIFT == 60
    X = art["chosen"]
    K = knots_of(F.replay([], 1)[1].K)[0]
    assert X == K[1:6] and art["atBound"] == [] and art["verify"] == 0.0     # the shipped knots are the artifact's


def test_the_mirror_reads_the_body_clocks_hour_not_the_worlds():
    # Plan 16 Task 4b: the stage's unfed dip reads the trace's body-clock hour (none with sleep off), never the world
    # age: a row at the world's 19:50 peak whose body clock reads the 07:50 trough takes the dip out
    import fit_hunger_curve as F
    C = {"A": 0.085, "PEAK": 19.8333, "FED_M": 3.80654, "DEAD_ZONE": 0.02, "HOLD_EPS": 0.001}
    knots = (0.097, 0.21125, 0.289531, 0.420782, 0.6825)
    X = (0.0,) + knots + (1.0,)
    row = {"age": 19.8333 - F.HOUR_OFFSET, "satiety.hModel": 0.25, "satiety.M": 0.0}
    trough = 1 - 0.085
    got = F.stage([dict(row, body=7.8333)], knots, C, 0.0)[0]
    assert got == pytest.approx(F.curve_map(0.25 / trough, X))
    assert F.stage([dict(row, body=None)], knots, C, 0.0)[0] == pytest.approx(F.curve_map(0.25, X))


def test_a_meal_that_never_reaches_peckish_before_the_next_reads_censored():
    import fit_hunger_curve as F
    H = [0.0] * (F.DAYS_THREE * F.DAY)
    mr = F.meal_returns(H)
    assert mr["breakfast"][0] == (5.0, True) and mr["lunch"][0] == (6.0, True) and mr["dinner"][0] == (13.0, True)


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


def test_the_mirror_reproduces_the_kernel(fit_any):
    # both sleep settings: the mirror reads the body clock's hour off the trace (none with sleep off)
    F = fit_any["F"]
    C = F.constants(fit_any["K"])
    X, _ = knots_of(fit_any["K"])
    for key in ("three", "fast"):
        rows = fit_any[key]
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


# ---- Plan 15 Task 6 fix 2: refeeding clears Starving, and an offline gap is not a fast -----------------------------

@pytest.mark.parametrize("kcal", [500.0, 600.0, 650.0, 690.0, 700.0, 1300.0])
def test_a_meal_after_a_120_h_fast_clears_the_starving_minimum_at_once(kcal):
    import fit_hunger_curve as F
    b = F.FED_DAYS * F.DAY + F.MEAL_MIN[0]
    m = b + 120 * 60
    ev = [e for e in F.fast_events() if e["kind"] != "autodrop"] + F.water(10)
    rows, be = F.replay(ev + [F.meal(m, kcal)], m + 240)
    fed_m = be.K.hungerCurve.FED_M
    assert rows[m - 1]["drain.starveAcute"] is True and rows[m - 1]["HUNGER"] > 0.70
    fed = [r for r in rows[m:] if r["satiety.M"] >= fed_m]
    assert fed and all(not r["drain.starveAcute"] and r["HUNGER"] < 0.70 for r in fed)
    assert rows[m]["HUNGER"] < 0.15                                       # the curve again, at once
    if kcal >= 700:
        assert rows[m + 30]["HUNGER"] < 0.15


def test_a_199_h_logout_after_the_pool_empties_is_not_a_fast():
    import fit_hunger_curve as F
    import replay_live as RL
    b = F.FED_DAYS * F.DAY + F.MEAL_MIN[0]
    leave = b + 6 * 60                                                    # the pool empty since about 4.6 h
    back = leave + 199 * 60
    n = back + 60
    be = RL.ServerReplay(hour_offset=F.HOUR_OFFSET, rng="half", sleep_allowed=False)
    ev = sorted((e for e in F.fast_events() + F.water(12) if e["minute"] < leave), key=lambda e: e["minute"])
    rows = RL.run(be, RL.synthetic_ages(n), ev, list(F.PATHS) + ["drain.starvedH"], start_age=0.0,
                  offline=set(range(leave, back)))
    after = [r for r in rows[back:] if not r.get("offline")]
    assert after and all(not r["drain.starveAcute"] for r in after)
    assert max(r["drain.starvedH"] for r in after) < 9.0                 # 6 h before, at most an hour's clamp and one back
    assert all(be.K.drain.starvePhase(r["drain.starvedH"]) == 0 for r in after)
    assert all(r["HUNGER"] < 0.69 for r in after)


# ---- Plan 15 Task 6 fix 3: the snack diet's tolerance, and a refeed of 601-690 kcal ---------------------------------

def test_the_end_of_the_starving_minimum_re_seeds_hunger_from_the_curve(host):
    # the last HUNGER over this minute's cap (the starving minimum or a lifted cap just ended) is not held
    h = host.call("hungerCurve.inverse", 0.30)
    st = host.table({"hunger": 0.71, "fed": False, "circ": 1.0})
    assert host.call("hungerCurve.write", h, st) == pytest.approx(0.71)       # no cap given: the fasting hold
    assert host.call("hungerCurve.write", h, st, 0.69) == pytest.approx(0.30)  # over the cap: re-seeded
    assert host.call("hungerCurve.write", h, st, 1.0) == pytest.approx(0.71)  # under a lifted cap: held


def refeed(kcal, hours):
    import fit_hunger_curve as F
    b = F.FED_DAYS * F.DAY + F.MEAL_MIN[0]
    m = b + 120 * 60
    ev = [e for e in F.fast_events() if e["kind"] != "autodrop"] + F.water(12)
    rows, be = F.replay(ev + [F.meal(m, kcal)], m + int(hours * 60))
    return rows, be, m


@pytest.mark.parametrize("kcal", [650.0, 690.0])
def test_a_601_to_690_kcal_refeed_holds_starving_off_and_hunger_follows_the_curve(kcal):
    # re-review N2: the meal counts in full from its eat (the stomach's calories), so Starving does not return while it
    # is absorbed, and HUNGER, re-seeded from the curve as the minimum ends, rises with the curve rather than parking
    rows, be, m = refeed(kcal, 24)
    after = rows[m:]
    assert all(not r["drain.starveAcute"] for r in after)
    hs = [r["HUNGER"] for r in after]
    assert max(hs) < 0.69 and hs[-1] > hs[6 * 60] > hs[60]                   # the curve's rise, never the cap
    m1 = [r["satiety.hModel"] for r in after]
    C = be.K.hungerCurve
    assert all(abs(H - C.map(x)) < 0.15 for H, x in zip(hs[::60], m1[::60]))  # the curve of h_model (dip and hold aside)


def test_a_600_kcal_refeed_is_low_and_starving_returns_only_as_the_pool_empties():
    # 600 is the fallback's boundary (600 or less): the meal is low, so Starving returns once the pool is unfed again,
    # never during its fed spell
    rows, be, m = refeed(600.0, 8)
    fed_m = be.K.hungerCurve.FED_M
    back = next(i for i in range(m, len(rows)) if rows[i]["drain.starveAcute"])
    assert all(r["satiety.M"] >= fed_m for r in rows[m:back]) and rows[back]["satiety.M"] < fed_m


def test_a_200_kcal_snack_every_33_h_holds_the_fallback_through_the_pipeline():
    # re-review N1: three absorbed snacks overshoot 600 by float rounding; the tolerance keeps every unfed hour acute
    import fit_hunger_curve as F
    n = 14 * F.DAY
    ev = [F.meal(k * 33 * 60 + 30, 200.0) for k in range(0, n // (33 * 60) + 1) if k * 33 * 60 + 30 < n] + F.water(14)
    rows, be = F.replay(ev, n)
    fed_m = be.K.hungerCurve.FED_M
    unfed = [i for i in range(96 * 60, n) if rows[i]["satiety.M"] < fed_m]
    assert len(unfed) > 8000 and all(rows[i]["drain.starveAcute"] for i in unfed)


def test_the_writer_re_seeds_hunger_when_the_starving_state_ends_unfed(host):
    inv = lambda H: host.call("hungerCurve.inverse", H)      # noqa: E731
    out = run(host, mode=1, hunger=0.71, hungerTarget=inv(0.3), fed=False, starving=False)
    assert out.hunger == pytest.approx(0.3)                              # not parked at the 0.69 cap
    out = run(host, mode=1, hunger=0.71, hungerTarget=inv(0.3), fed=False, starving=True)
    assert out.hunger == pytest.approx(0.71)                             # still starving (chronic): the hold stands


# ---- Plan 19 Task 3a review M5: fit_hunger_curve's registry-read constants are the kernel's -------------------------

def test_the_fit_tools_registry_constants_are_the_kernels_and_its_knots_never_write_the_registry():
    import fit_hunger_curve as F
    from .conftest import LuaHost
    h = LuaHost()                                   # a fresh host: set_knots writes its kernel table
    K = h.K
    c = K.hybrid.defaults()
    assert F.CAP == c.hungerCap and F.STARVING_MIN == c.starvingMin
    assert F.THRESHOLDS == tuple(K.hungerCurve.THRESHOLDS[i] for i in range(1, 5))
    assert F.Y == tuple(K.hungerCurve.Y[i] for i in range(1, 8))
    F.set_knots(K, F.START)
    assert K.hungerCurve.X[3] == F.START[1]
    assert h.G.NutritionRevamp.data.dials["hungerCurve.X.3"].value == 0.21125
