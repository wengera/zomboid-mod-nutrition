"""Tests for tools/vanilla_model.py: each formula pinned to the value its register row gives (Plan 14 Task 2)."""
import csv, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import vanilla_model as vm
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DAY = 86400.0


def _series(out, name):
    return [v for _, v in out[name]]


def _at(out, name, hour):
    for t, v in out[name]:
        if abs(t - hour) < 1e-9:
            return v
    raise KeyError(hour)


def _first_hour(out, name, pred):
    for t, v in out[name]:
        if pred(v):
            return t
    return None


# ---- FORMULAS ------------------------------------------------------------------------------------------------
def test_formulas_cover_the_source_map_names():
    assert set(vm.FORMULAS) == {"VM%d" % i for i in range(1, 18)} | {"JT1"}
    for name, f in vm.FORMULAS.items():
        assert f["claims"] and f["doc"].strip(), name


def test_formula_claims_are_live_register_rows():
    with open(os.path.join(REPO, "docs", "reference", "claims.tsv"), encoding="utf-8") as fh:
        rows = {r["id"]: r for r in csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)}
    for name, f in vm.FORMULAS.items():
        for cid in f["claims"]:
            if cid.startswith("T2."):
                continue   # the provisional JT1 rows, minted by the controller
            assert cid in rows, (name, cid)
            assert rows[cid]["status"] != "superseded", (name, cid)


# ---- VM1: hunger awake ----------------------------------------------------------------------------------------
def test_vm1_rate_0470():
    # #0470: 9.6e-6 a game-second at H 0, StatsDecrease 3
    assert vm.hunger_rate_awake(0.0) == pytest.approx(9.6e-6, rel=1e-12)
    # #0474: the (1 - H) damping; #0470's fit 7.4916e-6 predicted at mean hunger 0.2196
    assert vm.hunger_rate_awake(0.2196) == pytest.approx(7.4916e-6, rel=5e-5)   # the mean is rounded


def test_vm1_time_constant_0490():
    # #0490: 104 167 game-seconds, 28.94 game-hours
    k = vm._hunger_k(False, False, False, 1.0, 1.0)
    assert 1.0 / k == pytest.approx(104167, abs=1)
    assert 1.0 / k / 3600 == pytest.approx(28.94, abs=0.005)


@pytest.mark.parametrize("target,hours,claim", [(0.15, 4.70, "#0492"), (0.25, 8.32, "#0493"),
                                                (0.45, 17.30, "#0494"), (0.70, 34.84, "#0495")])
def test_vm1_moodle_hours(target, hours, claim):
    assert vm.hours_to_hunger(target) == pytest.approx(hours, abs=0.005), claim


def test_vm1_appetite_traits_0492():
    # #0492: level 1 at 3.13 h with Hearty Appetite (x1.5), 6.27 h with Light Eater (x0.75);
    # the row's 3.13 is 3.1350 cut, not rounded, so the band is 0.006
    assert vm.hours_to_hunger(0.15, appetite=1.5) == pytest.approx(3.13, abs=0.006)
    assert vm.hours_to_hunger(0.15, appetite=0.75) == pytest.approx(6.27, abs=0.005)


def test_vm1_stats_decrease_0483():
    assert [vm.stats_decrease_multiplier(i) for i in range(1, 6)] == [2.0, 1.6, 1.0, 0.8, 0.65]
    assert vm.hunger_rate_awake(0.0, stats_mult=vm.stats_decrease_multiplier(1)) == pytest.approx(1.92e-5)


def test_vm1_simulated_hunger_matches_the_moodle_hours():
    out = vm.simulate({"hours": 36, "dt_min": 1, "start": {"hunger": 0.0}, "events": []})
    for target, hours in ((0.15, 4.70), (0.70, 34.84)):
        assert _first_hour(out, "hunger", lambda v, x=target: v > x) == pytest.approx(hours, abs=1 / 60 + 0.005)
    # S1b: the HUNGRY level series crosses at the same hours
    assert _first_hour(out, "hungry_level", lambda v: v >= 4) == pytest.approx(34.84, abs=1 / 60 + 0.005)


def test_vm1_rate_resumes_0525():
    # #0525: 9.2551e-6 predicted at a mean hunger of 0.0359
    assert vm.hunger_rate_awake(0.0359) == pytest.approx(9.2551e-6, rel=5e-5)   # the mean is rounded


def test_vm1_dt_is_honoured_and_exact():
    a = vm.simulate({"hours": 10, "dt_min": 1, "events": []})
    b = vm.simulate({"hours": 10, "dt_min": 30, "events": []})
    assert len(a["hunger"]) == 601 and len(b["hunger"]) == 21
    assert _at(a, "hunger", 10.0) == pytest.approx(_at(b, "hunger", 10.0), rel=1e-12)


# ---- VM2: exercising and asleep -------------------------------------------------------------------------------------
def test_vm2_exercise_rates_0471():
    assert vm.hunger_rate_awake(0.0, exercising=True) == pytest.approx(6.4e-6)
    assert vm.hunger_rate_awake(0.0, exercising=True, timer_up=True) == pytest.approx(1.92e-5)


def test_vm2_asleep_0498():
    # #0498: asleep, hunger rises 0.0864 x (1 - H) a game-day, 0 with the moodle up (#2783)
    assert vm.hunger_rate_asleep(0.0) * DAY == pytest.approx(0.0864)
    assert vm.hunger_rate_asleep(0.5) * DAY == pytest.approx(0.0432)
    assert vm.hunger_rate_asleep(0.0, timer_up=True) == 0.0


def test_vm2_simulated_sleep_and_running():
    out = vm.simulate({"hours": 1, "dt_min": 1, "events": [{"t_h": 0, "kind": "sleep", "duration_h": 1}]})
    assert _at(out, "hunger", 1.0) == pytest.approx(1 - vm.math.exp(-1e-6 * 3600), rel=1e-9)
    out = vm.simulate({"hours": 1, "dt_min": 1,
                       "events": [{"t_h": 0, "kind": "exercise", "mode": "running", "duration_min": 60}]})
    assert _at(out, "hunger", 1.0) == pytest.approx(1 - vm.math.exp(-6.4e-6 * 3600), rel=1e-9)


# ---- VM3: the food-eaten timer --------------------------------------------------------------------------------------
def test_vm3_fill_gate_3597():
    # #3597, #0054: no fill unless HUNGER is at its minimum after the eat
    assert vm.food_timer_fill(0.0, 0.01, -0.24) == 0.0
    assert vm.food_timer_fill(0.0, 0.0, -0.24) == pytest.approx(3120.0)        # #0503: x 13000
    assert vm.food_timer_fill(0.0, 0.0, -0.24, cooked=True) == pytest.approx(6240.0)   # #0054: x2 cooked
    assert vm.food_timer_fill(0.0, 0.0, -1.0) == 11000.0                       # #0054: cap


def test_vm3_decay_0529():
    # #0529: day length / 30 units a game-second, 3.0 at 90 minutes, 2.0 at 60
    assert vm.food_timer_decay_per_s(90) == pytest.approx(3.0)
    assert vm.food_timer_decay_per_s(60) == pytest.approx(2.0)


def test_vm3_cap_lasts_0528():
    # #0528: 11 000 / 3.0 = 3 667 game-seconds, 1.02 game-hours; a 1600-unit level about 8.9 game-minutes
    assert vm.FOOD_TIMER_CAP / vm.food_timer_decay_per_s() == pytest.approx(3667, abs=0.5)
    assert 1600 / vm.food_timer_decay_per_s() / 60 == pytest.approx(8.9, abs=0.05)


def test_vm3_levels_0511():
    assert [vm.food_eaten_level(x) for x in (0, 1, 1600, 1601, 3201, 4801, 197597)] == [0, 1, 1, 2, 3, 4, 4]


def test_vm3_h1_second_arm_freeze():
    # the map's H1 arm B: eat the bolognese (-0.24) at 0.10, HUNGER to 0, a 3120-unit freeze of 1040 s
    out = vm.simulate({"hours": 1, "dt_min": 1, "start": {"hunger": 0.10},
                       "events": [{"t_h": 0, "kind": "eat", "hunger_script": -24, "calories": 540}]})
    assert _at(out, "food_timer", 0.0) == pytest.approx(3120.0)
    assert _at(out, "hunger", 17 / 60) == 0.0
    assert _at(out, "hunger", 18 / 60) > 0.0
    assert _at(out, "hunger", 18 / 60) == pytest.approx(1 - vm.math.exp(-9.6e-6 * (1080 - 1040)), rel=1e-9)


def test_vm3_h1_first_arm_no_freeze():
    out = vm.simulate({"hours": 1, "dt_min": 1, "start": {"hunger": 0.25},
                       "events": [{"t_h": 0, "kind": "eat", "hunger_script": -24}]})
    assert _at(out, "hunger", 0.0) == pytest.approx(0.01)
    assert _at(out, "food_timer", 0.0) == 0.0
    assert _at(out, "hunger", 1 / 60) > 0.01


def test_vm3_frozen_0524():
    # #0524: at FOOD_EATEN level 4 and idle, hunger frozen at 0.200000 over 3 833 game-seconds
    out = vm.simulate({"hours": 1.065, "dt_min": 1.065 * 60 / 71, "start": {"hunger": 0.2, "food_timer": 197597},
                       "events": []})
    assert set(_series(out, "hunger")) == {0.2}


# ---- VM4: the eat -------------------------------------------------------------------------------------------------
def test_vm4_script_scale_0011():
    assert vm.script_to_stat(-16) == pytest.approx(-0.16)


@pytest.mark.parametrize("state,value,claim", [("cooked", -0.208, "#0029"), ("burnt", -0.0533, "#0030"),
                                               ("rotten", -0.0727, "#0032"), ("fresh", -0.16, "#0003")])
def test_vm4_apple_ladder(state, value, claim):
    assert vm.effective_hunger_change(-0.16, state) == pytest.approx(value, abs=5e-5), claim


def test_vm4_stale_and_floor_0031():
    assert vm.effective_hunger_change(-0.13, "stale") == pytest.approx(-0.1)
    assert vm.effective_hunger_change(-0.02, "rotten") == pytest.approx(-0.01)


def test_vm4_clamp_0021():
    out = vm.simulate({"hours": 0, "dt_min": 1, "start": {"hunger": 0.1},
                       "events": [{"t_h": 0, "kind": "eat", "hunger_change": -0.5}]})
    assert _at(out, "hunger", 0.0) == 0.0


def test_vm4_fraction():
    out = vm.simulate({"hours": 0, "dt_min": 1, "start": {"hunger": 0.5, "calories": 0.0},
                       "events": [{"t_h": 0, "kind": "eat", "hunger_change": -0.24, "fraction": 0.5,
                                   "calories": 540}]})
    assert _at(out, "hunger", 0.0) == pytest.approx(0.38)
    assert _at(out, "calories_store", 0.0) == pytest.approx(270)


# ---- VM5: thirst -----------------------------------------------------------------------------------------------------
def test_vm5_full_thirst_0496():
    # #0496: 1.0 in 34.72 game-hours plain, 17.36 with High Thirst, 69.44 with Low Thirst
    assert 1.0 / vm.thirst_rate() / 3600 == pytest.approx(34.72, abs=0.005)
    assert 1.0 / vm.thirst_rate(thirst_trait=2.0) / 3600 == pytest.approx(17.36, abs=0.005)
    assert 1.0 / vm.thirst_rate(thirst_trait=0.5) / 3600 == pytest.approx(69.44, abs=0.005)


def test_vm5_moodle_hours():
    out = vm.simulate({"hours": 30, "dt_min": 1, "events": []})
    # #0492: level 1 at 4.17 h; #0495: level 4 at 29.17 h
    assert _first_hour(out, "thirst_level", lambda v: v >= 1) == pytest.approx(4.17, abs=1 / 60 + 0.005)
    assert _first_hour(out, "thirst_level", lambda v: v >= 4) == pytest.approx(29.17, abs=1 / 60 + 0.005)


def test_vm5_measured_rate_0476():
    assert vm.thirst_rate() == pytest.approx(7.99999e-6, rel=2e-6)
    # #0524: thirst ran at 7.99989e-6 in the frozen-hunger samples
    assert vm.thirst_rate() == pytest.approx(7.99989e-6, rel=2e-5)


def test_vm5_asleep_0498():
    assert vm.thirst_rate(asleep=True) * DAY == pytest.approx(0.0864)


def test_vm5_water_2928():
    out = vm.simulate({"hours": 0, "dt_min": 1, "start": {"thirst": 0.8},
                       "events": [{"t_h": 0, "kind": "drink", "fluid": "water", "litres": 1.0}]})
    assert _at(out, "thirst", 0.0) == pytest.approx(0.3)


def test_vm5_thresholds_strict_0508_0509():
    assert [vm.moodle_level(x, vm.HUNGRY_THRESHOLDS) for x in (0.10, 0.15, 0.16, 0.26, 0.46, 0.71)] == \
        [0, 0, 1, 2, 3, 4]
    assert [vm.moodle_level(x, vm.THIRST_THRESHOLDS) for x in (0.10, 0.12, 0.13, 0.26, 0.71, 0.85)] == \
        [0, 0, 1, 2, 3, 4]


# ---- VM6: calorie burn -------------------------------------------------------------------------------------------
@pytest.mark.parametrize("state,mod,per_day,claim", [
    ("asleep", 1, 259.2, "#0454"), ("idle", 1, 1382.4, "#0455"), ("walking", 1, 6739.2, "#0457"),
    ("running", 1, 11232, "#0458"), ("sprinting", 1, 14601.6, "#0459"), ("idle", 8, 11059.2, "#0460"),
    ("idle", 0.5, 691.2, "#0460"), ("running", 8, 11232, "#0462"), ("walking", 8, 6739.2, "#0462")])
def test_vm6_burn_per_day(state, mod, per_day, claim):
    assert vm.burn_rate(state, 80, mod) * DAY == pytest.approx(per_day, rel=1e-9), claim


@pytest.mark.parametrize("w,per_day", [(100, 1728), (120, 2073.6), (60, 1036.8)])
def test_vm6_weight_scaling_0461(w, per_day):
    assert vm.burn_rate("idle", w) * DAY == pytest.approx(per_day, rel=1e-9)


def test_vm6_fitness_modifier_2187():
    assert vm.burn_rate("idle", 80, vm.FITNESS_MOD) == pytest.approx(0.048)
    out = vm.simulate({"hours": 1, "dt_min": 1, "start": {"calories": 0.0},
                       "events": [{"t_h": 0, "kind": "exercise", "mode": "pushups", "duration_min": 60}]})
    assert _at(out, "calories_store", 1.0) == pytest.approx(-0.048 * 3600, rel=1e-3)


def test_vm6_simulated_idle_day_0455():
    out = vm.simulate({"hours": 1, "dt_min": 1, "start": {"calories": 1000}, "events": []})
    assert 1000 - _at(out, "calories_store", 1.0) == pytest.approx(57.6, rel=1e-9)


# ---- VM7: the stores ----------------------------------------------------------------------------------------------
def test_vm7_drains_0069_0168():
    out = vm.simulate({"hours": 24, "dt_min": 60, "start": {"carbs": 500, "lipids": 500, "proteins": 500},
                       "events": []})
    assert 500 - _at(out, "carbs", 24.0) == pytest.approx(302.4)          # #0168
    assert 500 - _at(out, "lipids", 24.0) == pytest.approx(0.00113 * DAY)  # #0069
    assert 500 - _at(out, "proteins", 24.0) == pytest.approx(0.00086 * DAY)


def test_vm7_clamps_0022_0023():
    out = vm.simulate({"hours": 0, "dt_min": 1, "start": {"calories": 3000},
                       "events": [{"t_h": 0, "kind": "eat", "hunger_change": 0, "calories": 9999, "carbs": 9999,
                                   "lipids": 9999, "proteins": 9999}]})
    assert _at(out, "calories_store", 0.0) == 3700.0
    assert _at(out, "carbs", 0.0) == 1000.0 and _at(out, "proteins", 0.0) == 1000.0
    out = vm.simulate({"hours": 72, "dt_min": 60, "start": {"calories": -2000, "carbs": -400}, "events": []})
    assert min(_series(out, "calories_store")) == -2200.0
    assert min(_series(out, "carbs")) == -500.0


def test_vm7_rotten_keeps_calories_0036():
    out = vm.simulate({"hours": 0, "dt_min": 1, "start": {"hunger": 0.0, "calories": 0.0},
                       "events": [{"t_h": 0, "kind": "eat", "hunger_change": -0.2, "state": "rotten",
                                   "calories": 532, "carbs": 99}]})
    assert _at(out, "calories_store", 0.0) == 532 and _at(out, "carbs", 0.0) == 99


# ---- VM8: weight ----------------------------------------------------------------------------------------------------
def test_vm8_thresholds_0149_0151():
    assert [vm.gain_threshold(w) for w in (70, 80, 90)] == [600, 1000, 1400]
    assert vm.loss_threshold(80) == 0 and vm.loss_threshold(60) == -300


def test_vm8_gain_rates_0152_0153():
    assert vm.weight_rate(80, 4000) * DAY == pytest.approx(1.12, abs=0.005)
    assert vm.weight_rate(80, 3700) * DAY == pytest.approx(1.039, abs=0.0005)
    assert vm.weight_rate(80, 3700, carbs=701) * DAY == pytest.approx(3.117, abs=0.0005)
    assert vm.weight_rate(80, 3700, lipids=401) * DAY == pytest.approx(2 * 1.0392, abs=0.0005)
    assert vm.weight_rate(80, 1000) == 0.0


def test_vm8_loss_rates_0154_0161():
    assert -vm.weight_rate(80, -2500) * DAY == pytest.approx(0.73, abs=0.005)
    assert -vm.weight_rate(80, -2200) * DAY == pytest.approx(0.646272, rel=1e-9)
    assert vm.weight_rate(60, -200) == 0.0


def test_vm8_fasting_run_0166():
    # #0166: from a 0 store at 80 kg, the floor at game-hour 39 against 38.2 at a flat 80 kg;
    # loss 0.204 kg on day 1 and 0.576 kg on day 2
    out = vm.simulate({"hours": 72, "dt_min": 1, "start": {"calories": 0.0, "weight_kg": 80.0}, "events": []})
    floor_h = _first_hour(out, "calories_store", lambda v: v <= -2200)
    assert 38.2 < floor_h <= 39.0
    w0, w1, w2, w3 = (_at(out, "weight_kg", h) for h in (0, 24, 48, 72))
    assert w0 - w1 == pytest.approx(0.204, abs=0.002)
    assert w1 - w2 == pytest.approx(0.576, abs=0.002)
    # #0160: 1.426 kg measured, 1.412 predicted over 72 game-hours, a 0.212 tolerance
    assert w0 - w3 == pytest.approx(1.426, abs=0.03)


def test_vm8_h2_gains_at_1500():
    # the map's H2: 3 x 500 kcal a day against 1382.4 burned, the store climbs above 1000 and vanilla gains
    ev = []
    for d in range(30):
        for h in (7, 12, 18):
            ev.append({"t_h": d * 24 + h, "kind": "eat", "hunger_change": -0.2, "calories": 500,
                       "carbs": 62.5, "lipids": 19.44, "proteins": 18.75})
    out = vm.simulate({"hours": 720, "dt_min": 10, "start": {"calories": 0.0}, "events": ev})
    assert _at(out, "weight_kg", 720.0) > 80.0


# ---- VM9: bands ------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("w,band", [(49.9, "EMACIATED"), (50, "EMACIATED"), (50.1, "VERY_UNDERWEIGHT"),
                                    (64.9, "VERY_UNDERWEIGHT"), (65, "VERY_UNDERWEIGHT"), (65.1, "UNDERWEIGHT"),
                                    (75, "UNDERWEIGHT"), (75.01, None), (80, None), (84.99, None),
                                    (85, "OVERWEIGHT"), (99.9, "OVERWEIGHT"), (100, "OBESE"), (105, "OBESE")])
def test_vm9_bands_0531_3069(w, band):
    assert vm.weight_band(w) == band


def test_vm9_creation_weights_0533():
    assert [vm.creation_weight(b) for b in ("OBESE", "OVERWEIGHT", "UNDERWEIGHT", "VERY_UNDERWEIGHT",
                                            "EMACIATED", None)] == [105, 95, 70, 60, 50, 80]


# ---- VM10: health ------------------------------------------------------------------------------------------------------
def test_vm10_rates_0518():
    assert vm.health_loss_per_hour(4, 0, 90) == pytest.approx(3.564)
    assert vm.health_loss_per_hour(4, 0, 60) == pytest.approx(2.376)
    assert vm.health_loss_per_hour(0, 4, 90) == pytest.approx(17.82)
    assert vm.health_loss_per_hour(0, 4, 60) == pytest.approx(11.88)
    assert vm.health_loss_per_hour(3, 3, 90) == 0.0


def test_vm10_measured_thirst_0519():
    assert vm.health_loss_per_hour(0, 4, 90) == pytest.approx(17.820029, rel=2e-6)


def test_vm10_starving_to_death():
    # S2d: HUNGER from 0 to 0.70 at 34.84 h, then 3.564 a game-hour: death about 62.9 h after the last meal
    out = vm.simulate({"hours": 70, "dt_min": 1, "start": {"hunger": 0.0, "thirst": 0.0},
                       "events": [{"t_h": h, "kind": "drink", "fluid": "water", "litres": 2.0}
                                  for h in range(0, 70, 6)]})
    assert _first_hour(out, "health", lambda v: v <= 0) == pytest.approx(62.9, abs=0.05)


# ---- VM11: Strength experience ---------------------------------------------------------------------------------------
def test_vm11_set_3844():
    assert vm.pushup_set_xp() == 360
    assert vm.strength_xp_grant(37500, 360)[1] == 360


@pytest.mark.parametrize("protein,xp,claim", [(100, 540, "#2112"), (-400, 252, "#2112"), (50, 360, "strict"),
                                              (300, 360, "strict"), (-300, 360, "strict"), (0, 360, "#3844")])
def test_vm11_protein_factor_2112(protein, xp, claim):
    assert vm.strength_xp_grant(37500, 360, proteins=protein)[1] == pytest.approx(xp), claim


def test_vm11_sandbox_and_sleep_3835_2161():
    assert vm.strength_xp_grant(37500, 360, xp_multiplier=2.0)[1] == 720
    assert vm.strength_xp_grant(37500, 360, asleep=True) == (37500, 0.0)


def test_vm11_thresholds_2102_2874_2109():
    assert vm.total_xp_for_level(5) == 37500
    assert vm.total_xp_for_level(10) == 487500
    assert [vm.total_xp_for_level(n) - vm.total_xp_for_level(n - 1) for n in range(1, 11)] == \
        [1500, 3000, 6000, 9000, 18000, 30000, 60000, 90000, 120000, 150000]
    assert vm.strength_xp_grant(487500, 360) == (487500, 0.0)
    assert vm.strength_xp_grant(487400, 360) == (487500, 100)
    assert vm.level_for_xp(37500) == 5 and vm.level_for_xp(37499) == 4


def test_vm11_level_crossing_in_simulation():
    # the map's V3 arm B: parked 300 XP under level 6 with protein 100, one set crosses to 6
    out = vm.simulate({"hours": 0.5, "dt_min": 10, "start": {"strength_level": 5, "strength_xp": 67200,
                                                             "proteins": 100},
                       "events": [{"t_h": 0, "kind": "exercise", "mode": "pushups"}]})
    assert _at(out, "strength_xp", 0.0) == pytest.approx(67740)
    assert _at(out, "strength_level", 0.0) == 6


def _weekly_sets(days):
    """20 sets a week, spread daily: three sets on six days and two on the seventh."""
    return [{"t_h": d * 24 + 10, "kind": "exercise", "mode": "pushups", "sets": 3 if d % 7 < 6 else 2}
            for d in range(days)]


def test_vm11_h3_factor_1_reaches_9_in_a_year():
    # H3-v-model-x1: 37 500 + 1043 sets x 360 = 412 980 XP after 365 days, level 9 (#2102: 337 500 to 487 500)
    out = vm.simulate({"hours": 365 * 24, "dt_min": 60, "settings": {"protein_factor": 1.0},
                       "events": _weekly_sets(365)})
    assert _at(out, "strength_xp", 365 * 24.0) == pytest.approx(37500 + 1043 * 360)
    assert _at(out, "strength_level", 365 * 24.0) == 9


def test_vm11_h3_factor_15_caps_at_10():
    # H3-v-model-x15 / S4b: x1.5 reaches the 487 500 cap inside the year and stops there (#2109)
    out = vm.simulate({"hours": 365 * 24, "dt_min": 60, "settings": {"protein_factor": 1.5},
                       "events": _weekly_sets(365)})
    assert _at(out, "strength_xp", 365 * 24.0) == 487500
    assert 0 < _first_hour(out, "strength_level", lambda v: v >= 10) < 365 * 24


def test_vm11_unfed_store_gives_07():
    # with no food the protein store drains below -300 (#0069) and every set earns 252 (#2112)
    out = vm.simulate({"hours": 200, "dt_min": 60,
                       "events": [{"t_h": 199, "kind": "exercise", "mode": "pushups"}]})
    assert _at(out, "proteins", 199.0) < -300
    assert _at(out, "strength_xp", 199.0) - _at(out, "strength_xp", 198.0) == pytest.approx(252)


# ---- VM12: rust --------------------------------------------------------------------------------------------------------
def test_vm12_rust_start_days_2155():
    def days_to_first_loss(timer):
        mod, xp, n = 0, 37500.0, 0
        while xp == 37500.0:
            timer, mod, xp, _ = vm.rust_tick(timer, mod, xp, 5)
            n += 1
        return n * 10 / 60 / 24
    assert days_to_first_loss(-50000.0) == pytest.approx(48.6, abs=0.05)
    assert days_to_first_loss(0.0) == pytest.approx(13.9, abs=0.05)


def test_vm12_rust_bucket_and_level_2868():
    # #2868: timer written to 30000, the next pass set strengthMod 25 and took 1 XP (37600 to 37599), level 3 held
    timer, mod, xp, level = vm.rust_tick(30000.0 - 10, 0, 37600.0, 3)
    assert (mod, xp, level) == (25, 37599.0, 3)
    timer, mod, xp, level = vm.rust_tick(timer, mod, xp, 3)
    assert xp == 37599.0
    # a level is lost once the experience falls below its total
    assert vm.rust_tick(30000.0, 0, 37500.0, 5)[2:] == (37499.0, 4)
    # the reset past 31000
    assert vm.rust_tick(31000.0, 25, 1.0, 0)[0] == 0.0


def test_vm12_grant_2156():
    assert vm.rust_after_grant(0.0) == -3000.0
    assert vm.rust_after_grant(-48000.0) == -50000.0


def test_vm12_idle_year_from_a_level_total():
    # #2155: from the -50000 default the first rust step is at 48.6 days; at the creation XP of exactly
    # 37 500 (#2874, #2104 setXPToLevel) that step leaves 37 499, below level 5's total, and
    # checkForLosingLevel takes the level to 4 (#2151, #2868's rule); 4 then holds for the year
    out = vm.simulate({"hours": 365 * 24, "dt_min": 60, "events": []})
    drop = _first_hour(out, "strength_level", lambda v: v < 5)
    assert drop / 24 == pytest.approx(48.6, abs=0.05)
    assert set(_series(out, "strength_level")) == {5, 4}
    # ten 1200-unit buckets (16 to 25) a cycle from 20 000 to the 31 000 reset: the first cycle ends at
    # 56.26 days, fourteen more of 21.54 days fit by day 365, the fifteenth stops short of its 13.9-day lead,
    # so 150 steps; each -1 goes through AddXP (#2130, #3836), and unfed the protein store is below -300 from
    # 300 / 0.00086 s = 4.04 days (#0069), so each step takes 0.7 (#2112)
    assert _at(out, "strength_xp", 365 * 24.0) == pytest.approx(37500 - 150 * 0.7)


def test_vm12_idle_year_pinned_factor_1():
    out = vm.simulate({"hours": 365 * 24, "dt_min": 60, "settings": {"protein_factor": 1.0}, "events": []})
    assert _at(out, "strength_xp", 365 * 24.0) == pytest.approx(37500 - 150)


def test_vm12_rust_step_asleep_is_dropped_2161():
    # the first rust step from -50 000 is tick 7 001 (#2155); asleep across it, AddXP drops the -1
    t = 7001 * 10 / 60
    awake = vm.simulate({"hours": t + 1, "dt_min": 60, "settings": {"protein_factor": 1.0}, "events": []})
    asleep = vm.simulate({"hours": t + 1, "dt_min": 60, "settings": {"protein_factor": 1.0},
                          "events": [{"t_h": t - 1, "kind": "sleep", "duration_h": 2}]})
    assert _at(awake, "strength_xp", float(int(t + 1))) == 37499
    assert _at(asleep, "strength_xp", float(int(t + 1))) == 37500


# ---- VM13 and JT1: trait start levels -----------------------------------------------------------------------------------
@pytest.mark.parametrize("trait,level", [(None, 5), ("WEAK", 0), ("FEEBLE", 3), ("STOUT", 7), ("STRONG", 9)])
def test_vm13_jt1_start_levels(trait, level):
    # #2104 seeds 5; #3878 the boosts -5, -2, +2, +4; #3879 the clamp to [0, 10]
    assert vm.start_strength_level(trait) == level


def test_vm13_profession_boost_and_clamp():
    assert vm.start_strength_level(None, 1) == 6
    assert vm.start_strength_level("STRONG", 2) == 10
    assert vm.start_strength_level("WEAK", -1) == 0
    assert vm.start_strength_level("WEAK", 1) == 1


# ---- VM14: what hunger does not read --------------------------------------------------------------------------------------
def test_vm14_hunger_ignores_weight_and_calories_0488():
    a = vm.simulate({"hours": 24, "dt_min": 10, "start": {"weight_kg": 60, "calories": -2000}, "events": []})
    b = vm.simulate({"hours": 24, "dt_min": 10, "start": {"weight_kg": 120, "calories": 3000}, "events": []})
    assert _series(a, "hunger") == _series(b, "hunger")
    assert _series(a, "calories_store") != _series(b, "calories_store")


# ---- VM15: coffee ---------------------------------------------------------------------------------------------------------
def test_vm15_coffee_2949():
    assert vm.fatigue_change(0.25) == pytest.approx(-0.025)
    assert vm.fatigue_change(0.2) == pytest.approx(-0.0199, abs=2e-4)   # #2949 measured 0.5765 to 0.5566
    on = vm.simulate({"hours": 0, "dt_min": 1, "start": {"fatigue": 0.5}, "settings": {"sleep_allowed": True},
                      "events": [{"t_h": 0, "kind": "drink", "fluid": "coffee", "litres": 0.25}]})
    off = vm.simulate({"hours": 0, "dt_min": 1, "start": {"fatigue": 0.5},
                       "events": [{"t_h": 0, "kind": "drink", "fluid": "coffee", "litres": 0.25}]})
    assert _at(on, "fatigue", 0.0) == pytest.approx(0.475)
    assert _at(off, "fatigue", 0.0) == 0.5


# ---- VM16: intoxication ----------------------------------------------------------------------------------------------------
def test_vm16_beer_2926_2923():
    assert vm.intoxication_gain(1.0 * vm.BEER_ALCOHOL_PER_L, 0.6) == pytest.approx(20)
    assert vm.intoxication_gain(0.5 * vm.BEER_ALCOHOL_PER_L, 0.0) == pytest.approx(10)
    assert vm.intoxication_gain(0.05, 0.7) == pytest.approx(25)
    assert vm.intoxication_gain(0.05, 0.81) == pytest.approx(22)
    # #2950: a 0.3 L can at HUNGER 0.46 predicts 6
    assert vm.intoxication_gain(0.3 * 0.05, 0.46) == pytest.approx(6)


def test_vm16_decay_2922_2951():
    assert vm.intoxication_decay_per_hour(90) == pytest.approx(45.36)
    assert vm.intoxication_decay_per_hour(60) == pytest.approx(30.24)
    assert vm.intoxication_decay_per_hour(15) == pytest.approx(7.5599, abs=2e-4)   # #2951 measured


def test_vm16_simulated_beer():
    out = vm.simulate({"hours": 1, "dt_min": 1, "start": {"hunger": 0.0},
                       "events": [{"t_h": 0, "kind": "drink", "fluid": "beer", "litres": 0.3}]})
    assert _at(out, "intoxication", 0.0) == pytest.approx(6)
    assert _at(out, "intoxication", 5 / 60) == pytest.approx(6 - 45.36 * 5 / 60)
    assert _at(out, "intoxication", 1.0) == 0.0


def test_vm16_spread_beer_0085():
    # a 0.3 L beer drunk over 1.5 game minutes: the 6 enters evenly and the decay runs from the first sip, so the
    # peak at the drink's end is 6 less 45.36 x the duration, and the zero comes 6 / 45.36 h after the first sip
    ev = [{"t_h": 0.1, "kind": "drink", "fluid": "beer", "litres": 0.3, "duration_min": 1.5}]
    out = vm.simulate({"hours": 0.5, "dt_min": 0.05, "start": {"hunger": 0.0}, "events": ev})
    dur = 1.5 / 60
    assert _at(out, "intoxication", 0.1 + dur) == pytest.approx(6 - 45.36 * dur, rel=1e-9)
    assert _at(out, "intoxication", 0.1 + dur / 2) == pytest.approx((6 / dur - 45.36) * dur / 2, rel=1e-9)
    assert _at(out, "intoxication", 0.1 + dur + 0.05) == pytest.approx(6 - 45.36 * (dur + 0.05), rel=1e-9)
    zero = next(t for t, v in out["intoxication"] if t > 0.1 and v == 0.0)
    assert zero == pytest.approx(0.1 + 6 / 45.36, abs=0.05 / 60 + 1e-9)
    # the instant drink is unchanged, and a spread water drink lowers thirst by the same total
    inst = vm.simulate({"hours": 0.5, "dt_min": 0.05, "start": {"hunger": 0.0},
                        "events": [dict(ev[0], duration_min=0)]})
    assert _at(inst, "intoxication", 0.1) == pytest.approx(6)
    w = vm.simulate({"hours": 0.2, "dt_min": 0.05, "start": {"thirst": 0.5},
                     "events": [{"t_h": 0.0, "kind": "drink", "fluid": "water", "litres": 0.4, "duration_min": 3}]})
    w0 = vm.simulate({"hours": 0.2, "dt_min": 0.05, "start": {"thirst": 0.5},
                      "events": [{"t_h": 0.0, "kind": "drink", "fluid": "water", "litres": 0.4}]})
    assert _at(w, "thirst", 0.2) == pytest.approx(_at(w0, "thirst", 0.2), abs=1e-12)
    assert "#0085" in vm.FORMULAS["VM16"]["claims"] and "#2925" in vm.FORMULAS["VM16"]["claims"]
    # the hunger factor reaches a spread drink: at HUNGER 0.7 the dose is 6 x 1.25 (#2923)
    hungry = vm.simulate({"hours": 0.5, "dt_min": 0.05, "start": {"hunger": 0.7}, "events": ev})
    assert _at(hungry, "intoxication", 0.1 + dur) == pytest.approx(6 * 1.25 - 45.36 * dur, rel=1e-6)


# ---- boundary probes (each threshold within 10 % on both sides) ------------------------------------------------------
def test_vm5_threshold_edges_0508_0509():
    assert [vm.moodle_level(x, vm.HUNGRY_THRESHOLDS) for x in (0.14, 0.16, 0.24, 0.26, 0.44, 0.46, 0.69, 0.71)] == \
        [0, 1, 1, 2, 2, 3, 3, 4]
    assert [vm.moodle_level(x, vm.THIRST_THRESHOLDS) for x in (0.11, 0.13, 0.24, 0.26, 0.69, 0.71, 0.83, 0.85)] == \
        [0, 1, 1, 2, 2, 3, 3, 4]


def test_vm3_level_edges_0511():
    assert [vm.food_eaten_level(x) for x in (1500, 1700, 3100, 3300, 4700, 4900)] == [1, 2, 2, 3, 3, 4]


def test_vm6_swing_0460():
    # #0460: a swing sets the modifier to 8.0, 0.128 kcal a game-second idle; #2774 it counts as exercising
    out = vm.simulate({"hours": 1, "dt_min": 1, "start": {"calories": 0.0},
                       "events": [{"t_h": 0, "kind": "exercise", "mode": "swing", "duration_min": 60}]})
    assert -_at(out, "calories_store", 1.0) == pytest.approx(0.128 * 3600, rel=1e-4)   # the weight falls a little
    assert _at(out, "hunger", 1.0) == pytest.approx(1 - vm.math.exp(-6.4e-6 * 3600), rel=1e-9)


def test_vm8_macro_edges_0153():
    base = vm.weight_rate(80, 3700)
    assert vm.weight_rate(80, 3700, carbs=650) == pytest.approx(2 * base)
    assert vm.weight_rate(80, 3700, lipids=380) == pytest.approx(base)
    assert vm.weight_rate(80, 3700, lipids=750) == pytest.approx(3 * base)


def test_vm11_protein_edges_2112():
    assert [vm.protein_factor(p) for p in (45, 52, 290, 310, -280, -320)] == [1.0, 1.5, 1.5, 1.0, 1.0, 0.7]


def test_vm16_hunger_edges_2923():
    assert [vm.intoxication_gain(0.05, h) for h in (0.58, 0.62, 0.75, 0.79, 0.82)] == \
        pytest.approx([20, 25, 25, 25, 22])


# ---- fix round 1: the review's M-1 cases ----------------------------------------------------------------------------
def test_m1_capped_set_leaves_the_rust_timer_and_rust_dips_to_9():
    # a set at the cap makes no change (#2109), so no positive AddXP and no -3000 (#2156): the timer runs on
    # from -50 000 and the first rust step (tick 7 001, #2155) takes the cap to 487 499, level 9
    t = 7001 * 10 / 60
    out = vm.simulate({"hours": t + 1, "dt_min": 60, "start": {"strength_level": 10},
                       "settings": {"protein_factor": 1.0},
                       "events": [{"t_h": 1, "kind": "exercise", "mode": "pushups"}]})
    assert _at(out, "strength_xp", 2.0) == 487500
    end = float(int(t + 1))
    assert _at(out, "strength_xp", end) == 487499 and _at(out, "strength_level", end) == 9


def test_m1_cooked_eat_fills_double_0054():
    out = vm.simulate({"hours": 0, "dt_min": 1, "start": {"hunger": 0.1},
                       "events": [{"t_h": 0, "kind": "eat", "hunger_script": -24, "state": "cooked"}]})
    assert _at(out, "food_timer", 0.0) == pytest.approx(0.312 * 13000 * 2)


def test_m1_beer_reads_live_hunger_2923():
    out = vm.simulate({"hours": 0, "dt_min": 1, "start": {"hunger": 0.7},
                       "events": [{"t_h": 0, "kind": "drink", "fluid": "beer", "litres": 0.3}]})
    assert _at(out, "intoxication", 0.0) == pytest.approx(7.5)


def test_m1_eat_thirst_scales_with_fraction():
    out = vm.simulate({"hours": 0, "dt_min": 1, "start": {"thirst": 0.5},
                       "events": [{"t_h": 0, "kind": "eat", "hunger_change": 0, "thirst_change": -0.1,
                                   "fraction": 0.5}]})
    assert _at(out, "thirst", 0.0) == pytest.approx(0.45)


def test_m1_asleep_burn_takes_the_modifier_0454():
    assert vm.burn_rate("asleep", 80, 8) * DAY == pytest.approx(2073.6)


def test_m1_timer_gate_is_hunger_at_zero_3597():
    assert vm.food_timer_fill(0.0, 0.0005, -0.24) == 0.0


def test_m1_first_rust_tick_hour_2155():
    # tick 7 001 from -50 000 is the first timer above 20 000: hour 7001 x 10 / 60 = 1166.83
    out = vm.simulate({"hours": 1168, "dt_min": 10, "settings": {"protein_factor": 1.0}, "events": []})
    assert _first_hour(out, "strength_xp", lambda v: v < 37500) == pytest.approx(7001 * 10 / 60, abs=1e-6)


def test_m2_sprinting_is_not_exercising_for_hunger_2774():
    out = vm.simulate({"hours": 1, "dt_min": 1,
                       "events": [{"t_h": 0, "kind": "exercise", "mode": "sprinting", "duration_min": 60}]})
    assert _at(out, "hunger", 1.0) == pytest.approx(1 - vm.math.exp(-9.6e-6 * 3600), rel=1e-9)


def test_m3_fresh_store_t2_3():
    out = vm.simulate({"hours": 0, "dt_min": 1, "events": []})
    assert _at(out, "calories_store", 0.0) == 800.0 and _at(out, "weight_kg", 0.0) == 80.0


# ---- #3881: the 35 kg weight floor (Nutrition.setWeight) -------------------------------------------------------------

def test_t24_floor_clamps_the_weight_and_drains_health():
    # a store pinned far below the loss threshold from 35.2 kg: the weight stops at 35.0 and health falls 178.2 a
    # game-hour once it is pressed on the floor (0.0165 a multiplier unit, 120 x 90 units a game-hour)
    assert vm.weight_floor_health_per_hour(90.0) == pytest.approx(178.2)
    out = vm.simulate({"hours": 8.0, "dt_min": 1.0, "start": {"weight_kg": 35.2, "calories": -2200.0}, "events": []})
    rate = -vm.weight_rate(35.2, -2200.0)
    t_floor = 0.2 / rate / 3600.0                                        # 7.43 h to reach the floor
    assert 7.0 < t_floor < 7.5
    assert min(w for _, w in out["weight_kg"]) == 35.0
    assert _at(out, "health", 7.0) == 100.0
    assert _at(out, "health", 7.6) == pytest.approx(100.0 - 178.2 * (7.6 - t_floor), abs=0.5)
    assert _at(out, "health", 8.0) == 0.0


def test_t24_no_drain_above_the_floor():
    out = vm.simulate({"hours": 24.0, "dt_min": 60.0, "start": {"weight_kg": 80.0, "calories": -2200.0}, "events": []})
    assert _at(out, "health", 24.0) == 100.0 and _at(out, "weight_kg", 24.0) < 80.0


# ---- VM17: food mood (Plan 19 Task 8) ------------------------------------------------------------------------------
def test_vm17_food_mood_by_hand():
    # one butter (UnhappyChange 20) at minute 0, no upkeep: UNHAPPINESS holds at 20 for ever (#3033)
    assert vm.food_mood([(0, 20.0, 0.0)], 60) == (20.0, 0.0)
    # with an upkeep of 6 a game hour (0.1 a minute) toward 0, the stat falls 0.1 a minute after the eat's minute
    u, b = vm.food_mood([(0, 20.0, 5.0)], 120, upkeep_h=6.0)
    assert u == pytest.approx(sum(20.0 - 0.1 * (t + 1) for t in range(120)) / 120)
    assert b == pytest.approx(sum(max(0.0, 5.0 - 0.1 * (t + 1)) for t in range(120)) / 120)
    # each stat is held in [0, 100] at the eat, and a happy food cannot take it under 0
    assert vm.food_mood([(0, 150.0, -30.0)], 1) == (100.0, 0.0)
    # a standing background: the upkeep moves the stat toward it from either side
    assert vm.food_mood([], 10, upkeep_h=60.0, bg=20.0) == (20.0, 20.0)
    assert vm.food_mood([(0, -5.0, 0.0)], 2, upkeep_h=60.0, bg=20.0)[0] == pytest.approx((16.0 + 17.0) / 2)


def test_vm17_refuses_an_eat_out_of_order_or_past_the_window():
    with pytest.raises(ValueError):
        vm.food_mood([(5, 1.0, 0.0), (2, 1.0, 0.0)], 10)
    with pytest.raises(ValueError):
        vm.food_mood([(10, 1.0, 0.0)], 10)


def test_t24_floor_seconds():
    assert vm.floor_seconds(36.0, -0.001, 2000.0) == pytest.approx(1000.0)
    assert vm.floor_seconds(35.0, -0.001, 600.0) == 600.0
    assert vm.floor_seconds(36.0, 0.001, 600.0) == 0.0
    assert vm.floor_seconds(80.0, -1e-5, 600.0) == 0.0
