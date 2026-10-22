import pytest

NAN = float("nan")


def run(host, **kw):
    inp, out, c = host.call("hybrid.input"), host.call("hybrid.output"), host.call("hybrid.defaults")
    for k, v in kw.items():
        inp[k] = v
    host.call("hybrid.write", inp, out, c)
    return out


def test_the_hunger_target_moved_from_the_takeover(host):
    assert host.call("deficit.hungerTarget", 1.0, 1.0) == 0
    assert host.call("deficit.hungerTarget", 0.5, 1.0) == pytest.approx(0.5)
    assert host.call("deficit.hungerTarget", 1.0, 1.5) == 0                    # no deficit floor (removed in Plan 11g Task 7 fix 1, ruling T7-1; 0.02 x 0.5 = 0.01 from Plan 11f Task 2c fix 1, 1.0 from Plan 11d Task 9d)
    assert host.call("deficit.hungerTarget", 0.5, 1.5) == pytest.approx(0.75)


def test_mode_1_writes_hunger_thirst_and_fatigue_under_their_caps(host):
    out = run(host, mode=1, hungerTarget=0.9, thirst=0.2, thirstTarget=0.95, fOwned=True, fS=0.3, fCirc=0.05,
              fOff=0.02)
    assert out.hunger == pytest.approx(0.69) and out.thirst == pytest.approx(0.83)
    assert out.fatigue == pytest.approx(0.37)


def test_frozen_or_unowned_fatigue_is_never_written(host):
    assert run(host, mode=1, fOwned=True, fFrozen=True, fS=0.3).fatigue is None
    assert run(host, mode=1, fOwned=False).fatigue is None


def test_a_nil_thirst_target_writes_no_thirst(host):
    out = run(host, mode=1, thirst=0.2, thirstTarget=None)
    assert out.thirst is None


def test_a_non_finite_thirst_target_writes_no_thirst(host):
    assert run(host, mode=1, thirst=0.2, thirstTarget=NAN).thirst is None


def test_a_non_finite_hunger_or_fatigue_target_writes_neither(host):
    # Plan 12 A5 (K2 B4): K.clamp passes a NaN through, so a NaN target is caught before it reaches HUNGER or FATIGUE,
    # as THIRST's already is; the other stat of the pair is still written
    out = run(host, mode=1, hungerTarget=NAN, fOwned=True, fS=0.3)
    assert out.hunger is None and out.fatigue == pytest.approx(0.3)
    out = run(host, mode=1, hungerTarget=0.4, fOwned=True, fS=0.3, fOff=NAN)
    assert out.fatigue is None and out.hunger == pytest.approx(host.call("hungerCurve.map", 0.4))


def test_the_sip_is_folded_into_the_thirst_write(host):
    out = run(host, mode=1, thirst=0.1, lastThirst=0.3, sipOK=True, thirstTarget=0.3)
    assert out.sip == pytest.approx(0.2) and out.thirst == pytest.approx(0.1)


def test_no_sip_is_counted_when_an_intake_landed_or_on_the_first_write(host):
    assert run(host, mode=1, thirst=0.1, lastThirst=0.3, sipOK=False, thirstTarget=0.3).sip == 0
    assert run(host, mode=1, thirst=0.1, lastThirst=None, sipOK=True, thirstTarget=0.3).sip == 0
    assert run(host, mode=1, thirst=0.4, lastThirst=0.3, sipOK=True, thirstTarget=0.3).sip == 0


def test_overlay_writes_no_hunger_thirst_or_fatigue(host):
    out = run(host, mode=2, hungerTarget=0.5, thirst=0.1, lastThirst=0.3, thirstTarget=0.3, fOwned=True, fS=0.3,
              panicTarget=10, panic=8)
    assert out.hunger is None and out.thirst is None and out.fatigue is None and out.sip == 0
    assert out.panic == 10


def test_panic_is_held_at_its_target_only_when_below(host):
    assert run(host, panic=8.7444, panicTarget=10).panic == 10
    assert run(host, panic=11, panicTarget=10).panic is None
    assert run(host, panic=0, panicTarget=0).panic is None
    assert run(host, panic=0, panicTarget=NAN).panic is None


def test_the_stress_and_sickness_floors_rise_by_elapsed_game_time(host):
    out = run(host, dtS=60, stress=0.0, stressTarget=0.1, foodSick=0, foodSickTarget=30)
    assert out.stress == pytest.approx(5.0e-5 * 60)
    assert out.foodSick == pytest.approx(25 / 3600 * 60)
    out = run(host, dtS=7200, stress=0.0, stressTarget=1.0)          # a step over 60 minutes integrates 60
    assert out.stress == pytest.approx(5.0e-5 * 3600)                # 0.18, not the unclamped 0.36


def test_a_zero_or_negative_step_rises_nothing(host):
    for dt in (0, -600):
        out = run(host, dtS=dt, stress=0.2, stressTarget=1.0, foodSick=0, foodSickTarget=30)
        assert out.stress in (None, pytest.approx(0.2))
        assert out.foodSick in (None, pytest.approx(0))


def test_unhappiness_rises_toward_its_target_and_releases_a_fall_once(host):
    out = run(host, dtS=60, unhappy=0, unhappyTarget=20, lastUnhappyTarget=0)
    assert out.unhappy == pytest.approx(22 / 3600 * 60) and out.unhappyTarget == 20
    out = run(host, dtS=60, unhappy=20, unhappyTarget=5, lastUnhappyTarget=20)
    assert out.unhappy == pytest.approx(5)
    out = run(host, dtS=60, unhappy=3, unhappyTarget=NAN, lastUnhappyTarget=0)
    assert out.unhappy is None and out.unhappyTarget == 0


def test_temperature_is_written_only_on_the_adjustments_far_side(host):
    assert run(host, temp=37.0, tempTarget=37.5, tempAdj=0.5).temp == 37.5
    assert run(host, temp=37.6, tempTarget=37.5, tempAdj=0.5).temp is None
    assert run(host, temp=37.6, tempTarget=37.2, tempAdj=-0.2).temp == 37.2
    assert run(host, temp=37.0, tempTarget=0, tempAdj=0).temp is None


def test_intoxication_is_written_when_finite(host):
    assert run(host, intoxTarget=12.5).intox == 12.5
    assert run(host, intoxTarget=None).intox is None
    assert run(host, intoxTarget=NAN).intox is None


def test_the_asleep_endurance_gain_is_scaled_by_rmod(host):
    out = run(host, asleep=True, endurance=0.6, lastEndurance=0.5, rmod=0.5)
    assert out.endurance == pytest.approx(0.55)
    assert run(host, asleep=False, endurance=0.6, lastEndurance=0.5, rmod=0.5).endurance is None
    assert run(host, asleep=True, endurance=0.4, lastEndurance=0.5, rmod=0.5).endurance is None


def test_the_unhappiness_floor_never_pulls_an_added_stat_down(host):
    # Plan 11e close: monotony's (and a food's) UNHAPPINESS add above a positive floor target is kept;
    # a target's fall subtracts only that fall
    out = run(host, dtS=60, unhappy=35, unhappyTarget=20, lastUnhappyTarget=20)
    assert out.unhappy is None
    out = run(host, dtS=60, unhappy=35, unhappyTarget=15, lastUnhappyTarget=20)
    assert out.unhappy == pytest.approx(30)


# --- Plan 11f Task 9b (ruling T9-1, T9-3): the BOREDOM floor, monotony's second target -------------------------------


def test_boredom_rises_toward_its_target_at_one_bored_level_a_game_hour(host):
    out = run(host, dtS=60, bored=0, boredTarget=20, lastBoredTarget=0)
    assert out.bored == pytest.approx(25 / 3600 * 60) and out.boredTarget == 20
    out = run(host, dtS=3600, bored=0, boredTarget=20, lastBoredTarget=0)
    assert out.bored == pytest.approx(20)


def test_a_falling_boredom_target_releases_its_fall_once(host):
    out = run(host, dtS=60, bored=20, boredTarget=5, lastBoredTarget=20)
    assert out.bored == pytest.approx(5)
    out = run(host, dtS=60, bored=3, boredTarget=0, lastBoredTarget=20)
    assert out.bored == 0                                               # never below 0
    out = run(host, dtS=60, bored=35, boredTarget=15, lastBoredTarget=20)
    assert out.bored == pytest.approx(30)                               # only the fall, whatever raised it


def test_a_boredom_at_or_over_its_target_is_left_alone(host):
    assert run(host, dtS=60, bored=35, boredTarget=20, lastBoredTarget=20).bored is None
    assert run(host, dtS=60, bored=0, boredTarget=0, lastBoredTarget=0).bored is None


def test_a_non_finite_boredom_target_reads_zero(host):
    out = run(host, dtS=60, bored=3, boredTarget=NAN, lastBoredTarget=0)
    assert out.bored is None and out.boredTarget == 0
    out = run(host, dtS=60, bored=3, boredTarget=None, lastBoredTarget=0)
    assert out.bored is None and out.boredTarget == 0


def test_the_default_input_writes_no_boredom(host):
    out = run(host, dtS=60)
    assert out.bored is None and out.boredTarget == 0 and out.unhappy is None


# --- Plan 11f Task 9b fix 1 (Rule 6): the floor holds a fall under FLOOR_EPS and folds it into the next write ------


def test_the_floor_epsilon_is_a_labelled_game_choice(host):
    assert host.K.hybrid.FLOOR_EPS == 0.05
    from .conftest import dial_line
    line = dial_line("hybrid.FLOOR_EPS")                                 # Plan 19: the provenance is the registry row's
    assert "game choice" in line and "Rule 6" in line and "Task 9b fix 1" in line


@pytest.mark.parametrize("stat", ["unhappy", "bored"])
def test_a_fall_under_the_epsilon_is_held_and_the_old_target_remembered(host, stat):
    out = run(host, dtS=60, **{stat: 10, stat + "Target": 9.97, "last" + stat.capitalize() + "Target": 10})
    assert out[stat] is None and out[stat + "Target"] == 10


@pytest.mark.parametrize("stat", ["unhappy", "bored"])
def test_held_falls_fold_into_the_next_write_with_no_drift(host, stat):
    # the remembered target stays 10 while the target falls 0.03, then 0.06 in all: the whole 0.06 is subtracted
    out = run(host, dtS=60, **{stat: 10, stat + "Target": 9.94, "last" + stat.capitalize() + "Target": 10})
    assert out[stat] == pytest.approx(9.94, abs=1e-12) and out[stat + "Target"] == 9.94


@pytest.mark.parametrize("stat", ["unhappy", "bored"])
def test_a_fall_to_zero_lands_whatever_its_size(host, stat):
    out = run(host, dtS=60, **{stat: 0.03, stat + "Target": 0, "last" + stat.capitalize() + "Target": 0.03})
    assert out[stat] == 0 and out[stat + "Target"] == 0


@pytest.mark.parametrize("stat,rise", [("unhappy", 22 / 60), ("bored", 25 / 60)])
def test_a_held_fall_still_lets_a_stat_under_its_target_rise(host, stat, rise):
    out = run(host, dtS=60, **{stat: 5, stat + "Target": 9.97, "last" + stat.capitalize() + "Target": 10})
    assert out[stat] == pytest.approx(5 + rise) and out[stat + "Target"] == 10


@pytest.mark.parametrize("stat", ["unhappy", "bored"])
def test_a_rising_target_is_remembered_as_it_is(host, stat):
    out = run(host, dtS=60, **{stat: 10, stat + "Target": 10.01, "last" + stat.capitalize() + "Target": 10})
    assert out[stat + "Target"] == 10.01


def test_the_boredom_rise_waits_while_panic_is_above_five_and_the_target_is_remembered(host):
    out = run(host, dtS=60, bored=0, boredTarget=30, lastBoredTarget=30, panic=7)
    assert out.bored is None and out.boredTarget == 30
    out = run(host, dtS=60, bored=0, boredTarget=30, lastBoredTarget=30, panic=5)
    assert out.bored == pytest.approx(25 / 60)


def test_the_panic_wait_does_not_hold_the_unhappiness_rise_or_a_boredom_fall(host):
    out = run(host, dtS=60, unhappy=0, unhappyTarget=30, lastUnhappyTarget=30, panic=7)
    assert out.unhappy == pytest.approx(22 / 60)
    out = run(host, dtS=60, bored=20, boredTarget=0, lastBoredTarget=10, panic=7)
    assert out.bored == pytest.approx(10)


# --- Plan 15 Task 5: option B, the caps lift at the crises --------------------------------------------------------
def test_the_caps_hold_under_level_4_with_no_crisis(host):
    c = host.call("hybrid.defaults")
    st = host.table({"starving": False, "dehydrated": False})
    assert host.call("hybrid.caps", st, c) == (0.69, 0, 0.83)
    assert host.call("hybrid.caps", host.table({}), c) == (0.69, 0, 0.83)       # absent flags read no crisis


def test_starvation_lifts_the_hunger_cap_and_holds_starving_above_level_4(host):
    c = host.call("hybrid.defaults")
    assert host.call("hybrid.caps", host.table({"starving": True, "starveAcute": True}), c) == (1, 0.71, 0.83)
    assert host.call("hybrid.caps", host.table({"starving": True}), c) == (1, 0, 0.83)   # the chronic onset (Task 6)
    assert c.starvingMin > host.K.hybrid.HUNGRY_4                               # vanilla's Starving shows (#0508's strict >)
    out = run(host, mode=1, starving=True, starveAcute=True, hungerTarget=0.3)
    assert out.hunger == pytest.approx(0.71)                                     # held at least 0.71
    out = run(host, mode=1, starving=True, starveAcute=True, hungerTarget=0.93)
    assert out.hunger == pytest.approx(host.call("hungerCurve.map", 0.93))       # the curve above it, to 1
    assert run(host, mode=1, starving=True, hungerTarget=1.4).hunger == 1
    assert run(host, mode=1, starving=False, hungerTarget=0.93).hunger == pytest.approx(0.69)
    assert run(host, mode=1, starving=True, hungerTarget=NAN).hunger is None    # a NaN target still writes nothing


def test_dehydration_lifts_the_thirst_cap(host):
    c = host.call("hybrid.defaults")
    assert host.call("hybrid.caps", host.table({"dehydrated": True}), c) == (0.69, 0, 1)
    out = run(host, mode=1, dehydrated=True, thirst=0.8, thirstTarget=0.92)
    assert out.thirst == pytest.approx(0.92)
    assert run(host, mode=1, dehydrated=False, thirst=0.8, thirstTarget=0.92).thirst == pytest.approx(0.83)
    out = run(host, mode=1, dehydrated=True, starving=True, starveAcute=True, hungerTarget=0.5, thirst=0.8,
              thirstTarget=0.95)
    assert (out.hunger, out.thirst) == (pytest.approx(0.71), pytest.approx(0.95))
    assert run(host, mode=2, dehydrated=True, starving=True, hungerTarget=0.9).hunger is None   # Overlay writes none


def test_level_4_is_vanillas_strict_threshold(host):
    S = host.K.hybrid.severe
    assert (host.K.hybrid.HUNGRY_4, host.K.hybrid.THIRST_4) == (0.70, 0.84)    # #0508, #0509
    assert S(0.70, 0.84) is False and S(0.69, 0.83) is False
    assert S(0.7001, 0) is True and S(0, 0.8401) is True and S(0.71, 0.9) is True


def test_the_re_applied_terms_are_vanillas_multiples_of_the_constant(host):
    R = host.K.hybrid.severeRate
    assert R(0, False, 0, 0, False) == (0, 0)
    assert R(4, True, 0, 0, False) == (1, 0)              # SICK 4 on an arm: the whole constant (#2356)
    assert R(4, False, 0, 0, False) == (0, 0)             # SICK 4 with neither arm: none
    assert R(3, True, 0, 0, False) == (0, 0)              # SICK 3: none
    assert R(0, False, 4, 0, False) == (1, 0)             # BLEEDING 4: the whole constant
    assert R(0, False, 3, 0, False) == (0, 0)
    f3, h3 = R(0, False, 0, 3, True)
    f4, h4 = R(0, False, 0, 4, True)
    assert (f3, h3) == (pytest.approx(0.5), pytest.approx(0.5))   # 0.1 x 1 / ((5 - 3) / 10): the constant over 2
    assert (f4, h4) == (pytest.approx(1.0), pytest.approx(1.0))   # the constant over 1
    assert R(0, False, 0, 2, True) == (0, 0) and R(0, False, 0, 4, False) == (0, 0)
    f, h = R(4, True, 4, 4, True)
    assert (f, h) == (pytest.approx(3.0), pytest.approx(1.0))
    assert (host.K.hybrid.HEAVY_ROLL, host.K.hybrid.HEAVY_STRAIN) == (0.1, 0.5)


def test_the_re_applied_rates_per_game_hour_match_the_registers_arithmetic(host):
    # #0516's 0.0165 constant over 120 x 90 multiplier units a game hour at DayLength 4 (#2922): SICK 4 and BLEEDING 4
    # take 178.2 a game hour, as #3881 states for the 35 kg floor's per-update term; the HUNGRY and THIRST terms the
    # constant also carries are 3.564 and 17.82 (#0518), which option B leaves to the mod's floors
    units_h = 120 * 90
    f, _ = host.K.hybrid.severeRate(4, True, 0, 0, False)
    assert f * 0.0165 * units_h == pytest.approx(178.2)
    f, _ = host.K.hybrid.severeRate(0, False, 0, 3, True)
    assert f * 0.0165 * units_h == pytest.approx(89.1)
    assert 0.0165 / 50 * units_h == pytest.approx(3.564) and 0.0165 / 10 * units_h == pytest.approx(17.82)
